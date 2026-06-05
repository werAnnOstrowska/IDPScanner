import { motion, useMotionValue, useTransform, useSpring } from 'framer-motion';
import { Link } from 'react-router-dom';
import React from 'react';
import docStackImg from './assets/documentStack.png';
import MouseTrail from './components/MouseTrail';

export default function LandingPage() {
  const x = useMotionValue(0);
  const y = useMotionValue(0);


  const rawRotateX = useTransform(y, [-1, 1], [7, -7]);
  const rawRotateY = useTransform(x, [-1, 1], [-7, 7]);

  const springConfig = { damping: 30, stiffness: 100, mass: 1 };
  const smoothRotateX = useSpring(rawRotateX, springConfig);
  const smoothRotateY = useSpring(rawRotateY, springConfig);

  const handleMouseMove = (event: React.MouseEvent<HTMLDivElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const mouseX = (event.clientX - rect.left - rect.width / 2) / (rect.width / 2);
    const mouseY = (event.clientY - rect.top - rect.height / 2) / (rect.height / 2);
    
    x.set(mouseX);
    y.set(mouseY);
  };

  const handleMouseLeave = () => {
    x.set(0);
    y.set(0);
  };

  return (
    <div className="landing-container">
      <MouseTrail />

      <nav className="navbar">
        <motion.h1 
          className="logo"
          initial={{ opacity: 0, x: -50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8 }}
        >
          IDPScanner
        </motion.h1>
      </nav>

      <main className="hero-section">
        <motion.div 
          className="hero-image-placeholder"
          initial={{ opacity: 0, x: -50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
          style={{ perspective: 1000 }}
        >
          <motion.img 
            src={docStackImg} 
            alt="Stos dokumentów IDP" 
            style={{ 
              maxWidth: '100%', 
              maxHeight: '100%', 
              objectFit: 'contain',
              rotateX: smoothRotateX,
              rotateY: smoothRotateY,
            }} 

          />
        </motion.div>

        <div className="hero-content">
            <motion.h2 
                className="glisten-header"
                initial={{ opacity: 0, x: -50 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.8, delay: 0.4 }}
            >
                Twój <span className="smart-word">inteligentny</span><br/>
                digitalizator<br/>
                dokumentów
            </motion.h2>

          <motion.h3
            initial={{ opacity: 0, x: -50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.6 }}
          >
            Ekstraktuj metadane, zapisuj<br/>
            edytowalny tekst na zdjęciu i<br/>
            zachowuj skan
          </motion.h3>

          <motion.p
            initial={{ opacity: 0, x: -50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.8 }}
          >
            Na telefonie, komputerze, ze skanu czy ze zdjęcia<br/>
            - lokalnie i darmowo
          </motion.p>

          <motion.div
            initial={{ opacity: 0, x: -50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 1.0 }}
            className="btn-container"
          >
            <Link to="/scanner" className="cta-button">
              <span>WYPRÓBUJ TERAZ</span>
            </Link>
          </motion.div>
        </div>
      </main>
    </div>
  );
}