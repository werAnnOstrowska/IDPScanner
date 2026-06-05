import { useEffect, useRef } from 'react';

export default function MouseTrail() {

  // DOM reference
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // component lifecycle
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // particle system
    let particles: { x: number; y: number; life: number }[] = [];
    
    // responsive canvas
    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    // input tracking 
    const onMouseMove = (e: MouseEvent) => {
      particles.push({ x: e.clientX, y: e.clientY, life: 1.0 });
    };
    window.addEventListener('mousemove', onMouseMove);

    // animation loop
    let animationFrameId: number;
    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      // visual blending 
      ctx.globalCompositeOperation = 'screen';
      
      // render engine 
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        
        const radius = 50 * p.life; 
        if (radius < 0.1) continue;

        const gradient = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, radius);
        gradient.addColorStop(0, `rgba(250, 204, 21, ${p.life * 0.04})`);
        gradient.addColorStop(1, 'rgba(250, 204, 21, 0)');

        ctx.beginPath();
        ctx.fillStyle = gradient;
        ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
        ctx.fill();
        
        // physics decay 
        p.life -= 0.02; 
      }
      
      // garbage collection
      particles = particles.filter((p) => p.life > 0);
      animationFrameId = requestAnimationFrame(render);
    };
    render();

    // memory cleanup
    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  // UI overlay
  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        pointerEvents: 'none',
        zIndex: 5, 
      }}
    />
  );
}