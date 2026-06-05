import torch
import torch.nn as nn
import torch.nn.functional as F


# receptive visual attention feature module
class RVAFM(nn.Module):
    def __init__(self, in_channels):
        super(RVAFM, self).__init__()
        inter_channels = max(in_channels // 4, 8)
        self.vertical_conv = nn.Conv2d(in_channels, inter_channels, kernel_size=(5, 1), padding=(2, 0))
        self.horizontal_conv = nn.Conv2d(in_channels, inter_channels, kernel_size=(1, 5), padding=(0, 2))
        self.fusion_conv = nn.Conv2d(inter_channels * 2, in_channels, kernel_size=1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        v_features = F.relu(self.vertical_conv(x))
        h_features = F.relu(self.horizontal_conv(x))
        fused = torch.cat([v_features, h_features], dim=1)
        attention_weights = self.sigmoid(self.fusion_conv(fused))
        return x * attention_weights + x

# resnet building block
class BasicBlock(nn.Module):
    def __init__(self, in_channels, out_channels, stride=1):
        super(BasicBlock, self).__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(out_channels)
        self.shortcut = nn.Sequential()
        if stride != 1 or in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(out_channels)
            )

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += self.shortcut(x)
        out = F.relu(out)
        return out

# main CRNN architecture
class CRNN(nn.Module):
    """
    Convolutional Recurrent Neural Network (ResNet + BiLSTM)
    """

    def __init__(self, num_classes):
        super(CRNN, self).__init__()

        # CTC blank token allocation 
        self.num_classes = num_classes + 1

        #CNN feature extraction
        self.in_channels = 64
        self.conv1 = nn.Conv2d(1, 64, kernel_size=5, stride=1, padding=2, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.rvafm = RVAFM(64)

        # residual layers
        self.layer1 = self._make_layer(64, num_blocks=2, stride=1)  # -> 32x256
        self.layer2 = self._make_layer(128, num_blocks=2, stride=2)  # -> 16x128
        self.layer3 = self._make_layer(256, num_blocks=2, stride=2)  # -> 8x64

        # sequence flattening
        self.pool = nn.AdaptiveAvgPool2d((1, None))


        #sequence modeling (RNN)
        hidden_size = 256
        self.rnn = nn.LSTM(256, hidden_size, bidirectional=True, num_layers=2, batch_first=False)

        # transcription layer
        self.fc = nn.Linear(hidden_size * 2, self.num_classes)

    # dynamic layer constructor
    def _make_layer(self, out_channels, num_blocks, stride):
        strides = [stride] + [1] * (num_blocks - 1)
        layers = []
        for s in strides:
            layers.append(BasicBlock(self.in_channels, out_channels, s))
            self.in_channels = out_channels
        return nn.Sequential(*layers)

    # forward propagation
    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.rvafm(out)
        out = self.layer1(out)
        out = self.layer2(out)
        out = self.layer3(out)

        out = self.pool(out)

        out = out.squeeze(2)

        out = out.permute(2, 0, 1)

        out, _ = self.rnn(out)

        out = self.fc(out)
        out = F.log_softmax(out, dim=2)
        return out