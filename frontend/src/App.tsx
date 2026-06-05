import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import LandingPage from './LandingPage'
import ScannerApp from './ScannerApp'
import './App.css'

function App() {
  return (
    <Router>
      <Routes>
        <Route path ="/" element={<LandingPage />} />
        <Route path ="/scanner" element={<ScannerApp />} />
      </Routes>
    </Router>
  )
}

export default App;