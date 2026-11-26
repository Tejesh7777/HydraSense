/**
 * Animated background water ripple & fluid particle canvas
 * Creates a subtle, high-tech glowing fluid effect behind the dashboard.
 */

(function () {
    const canvas = document.getElementById('water-background-canvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let width, height;
    let particles = [];
    const particleCount = 45;
    let ripples = [];

    function resize() {
        width = canvas.width = window.innerWidth;
        height = canvas.height = window.innerHeight;
    }

    window.addEventListener('resize', resize);
    resize();

    // Fluid particles
    for (let i = 0; i < particleCount; i++) {
        particles.push({
            x: Math.random() * width,
            y: Math.random() * height,
            radius: Math.random() * 2.5 + 1.0,
            vx: (Math.random() - 0.5) * 0.4,
            vy: (Math.random() - 0.5) * 0.4 - 0.2, // gentle upward drift
            alpha: Math.random() * 0.4 + 0.1,
            pulse: Math.random() * Math.PI
        });
    }

    // Add ripple on mouse click
    window.addEventListener('click', (e) => {
        ripples.push({
            x: e.clientX,
            y: e.clientY,
            radius: 2,
            maxRadius: 70 + Math.random() * 40,
            alpha: 0.5,
            color: '0, 240, 255'
        });
    });

    let waveOffset = 0;

    function animate() {
        ctx.clearRect(0, 0, width, height);

        // 1. Draw subtle ambient fluid wave at the bottom
        waveOffset += 0.012;
        ctx.beginPath();
        ctx.moveTo(0, height);
        for (let x = 0; x <= width; x += 25) {
            const y = height - 60 + Math.sin(x * 0.003 + waveOffset) * 20 + Math.cos(x * 0.005 + waveOffset * 0.7) * 12;
            ctx.lineTo(x, y);
        }
        ctx.lineTo(width, height);
        ctx.closePath();
        ctx.fillStyle = 'rgba(0, 180, 255, 0.025)';
        ctx.fill();

        // 2. Draw connecting particle network (cyber fluid web)
        for (let i = 0; i < particles.length; i++) {
            const p = particles[i];
            p.x += p.vx;
            p.y += p.vy;
            p.pulse += 0.02;

            if (p.x < 0) p.x = width;
            if (p.x > width) p.x = 0;
            if (p.y < 0) p.y = height;
            if (p.y > height) p.y = 0;

            const currentAlpha = p.alpha + Math.sin(p.pulse) * 0.1;

            ctx.beginPath();
            ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(0, 240, 255, ${Math.max(0.05, currentAlpha)})`;
            ctx.shadowBlur = 8;
            ctx.shadowColor = 'rgba(0, 240, 255, 0.4)';
            ctx.fill();
            ctx.shadowBlur = 0;

            // Connect nearby particles
            for (let j = i + 1; j < particles.length; j++) {
                const p2 = particles[j];
                const dx = p.x - p2.x;
                const dy = p.y - p2.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 110) {
                    ctx.beginPath();
                    ctx.moveTo(p.x, p.y);
                    ctx.lineTo(p2.x, p2.y);
                    ctx.strokeStyle = `rgba(0, 240, 255, ${(1 - dist / 110) * 0.08})`;
                    ctx.lineWidth = 0.8;
                    ctx.stroke();
                }
            }
        }

        // 3. Draw water ripples
        for (let k = ripples.length - 1; k >= 0; k--) {
            const r = ripples[k];
            r.radius += 2.2;
            r.alpha -= 0.015;

            ctx.beginPath();
            ctx.arc(r.x, r.y, r.radius, 0, Math.PI * 2);
            ctx.strokeStyle = `rgba(${r.color}, ${Math.max(0, r.alpha)})`;
            ctx.lineWidth = 1.4;
            ctx.stroke();

            if (r.alpha <= 0 || r.radius >= r.maxRadius) {
                ripples.splice(k, 1);
            }
        }

        requestAnimationFrame(animate);
    }

    animate();
})();
