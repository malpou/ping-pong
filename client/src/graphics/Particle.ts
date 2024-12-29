import p5 from 'p5';
import { Engine, World, Bodies, Body, IBodyDefinition } from 'matter-js';

// Particle Class
class Particle {
  body: Body;
  radius: number;
  lifetime: number;
  fillRed: number;
  fillGreen: number;
  fillBlue: number;

  constructor(
    x: number,
    y: number,
    radius: number,
    lifetime: number,
    engine: Engine, // Pass the engine here
    options: IBodyDefinition = {}
  ) {
    // Default options for Matter.js body
    const defaultOptions: IBodyDefinition = {
      restitution: 0.8,
      friction: 0.3,
      density: 0.01,
      frictionAir: 0.01,
      ...options, // Allow overriding options
    };

    // Create a Matter.js body
    this.body = Bodies.circle(x, y, radius, defaultOptions);

    // Add the body to the world
    World.add(engine.world, this.body);

    // Store properties for rendering
    this.fillRed = Math.floor(Math.random() * 255)
    this.fillGreen = Math.floor(Math.random() * 255)
    this.fillBlue = Math.floor(Math.random() * 255)
    this.radius = radius;
    this.lifetime = lifetime; // Fade-out effect
  }

  // Update particle position and state
  update(engine: Engine): boolean {
    // Reduce lifetime (fade-out effect)
    this.lifetime -= 5;

    // Remove the particle if lifetime ends
    if (this.lifetime <= 0) {
      World.remove(engine.world, this.body);
      return false; // Signal that it should be removed
    }
    return true;
  }

  // Render the particle using p5.js
  show(p: p5): void {
    const pos = this.body.position;
    const angle = this.body.angle;

    p.push();
    p.translate(pos.x, pos.y);
    p.rotate(angle);

    // Set fill color with fading alpha
    p.fill(this.fillRed, this.fillGreen, this.fillBlue, this.lifetime);
    p.noStroke();
    p.ellipse(0, 0, this.radius * 2);

    p.pop();
  }
}

export default Particle;
