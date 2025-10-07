#!/usr/bin/env python3

"""
Modern Arkanoid Game - Professional Implementation

A high-performance, memory-efficient Arkanoid game with modern GUI design.
"""

import pygame
import math
import random
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Callable
from enum import Enum
from functools import lru_cache
import numpy as np

# Initialize Pygame
pygame.init()

class GameState(Enum):
    """Game state enumeration for state machine pattern."""
    MENU = 1
    PLAYING = 2
    PAUSED = 3
    GAME_OVER = 4
    VICTORY = 5

class PowerUpType(Enum):
    """Power-up types for game bonuses."""
    EXPAND_PADDLE = 1
    MULTI_BALL = 2
    SLOW_BALL = 3
    LASER = 4
    STICKY_PADDLE = 5
    EXTRA_LIFE = 6

@dataclass
class ColorScheme:
    """Modern color scheme with gradients."""
    BACKGROUND_TOP = (20, 20, 40)
    BACKGROUND_BOTTOM = (40, 20, 60)
    PADDLE = (100, 200, 255)
    PADDLE_GLOW = (150, 220, 255)
    BALL = (255, 255, 200)
    BALL_TRAIL = (255, 255, 150, 100)
    # Brick colors by strength
    BRICK_COLORS = {
        1: (255, 100, 100),  # Red
        2: (255, 200, 100),  # Orange
        3: (255, 255, 100),  # Yellow
        4: (100, 255, 100),  # Green
        5: (100, 200, 255),  # Blue
    }
    PARTICLE = (255, 255, 200, 200)
    TEXT_PRIMARY = (255, 255, 255)
    TEXT_SECONDARY = (200, 200, 200)
    TEXT_SHADOW = (50, 50, 50)

class Vector2D:
    """2D Vector class for physics calculations."""
    __slots__ = ['x', 'y']  # Memory optimization

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def __add__(self, other):
        return Vector2D(self.x + other.x, self.y + other.y)

    def __mul__(self, scalar: float):
        return Vector2D(self.x * scalar, self.y * scalar)

    def normalize(self):
        magnitude = math.sqrt(self.x**2 + self.y**2)
        return Vector2D(self.x / magnitude, self.y / magnitude) if magnitude > 0 else self

    def reflect(self, normal):
        dot = 2 * (self.x * normal.x + self.y * normal.y)
        return Vector2D(self.x - dot * normal.x, self.y - dot * normal.y)

    @property
    def magnitude(self):
        return math.sqrt(self.x**2 + self.y**2)

class Particle:
    """Particle effect for visual enhancement."""
    __slots__ = ['pos', 'vel', 'life', 'color', 'size']

    def __init__(self, x: float, y: float, vel: Vector2D, color: Tuple[int, ...]):
        self.pos = Vector2D(x, y)
        self.vel = vel
        self.life = 1.0
        self.color = color
        self.size = random.uniform(2, 5)

    def update(self, dt: float):
        self.pos = self.pos + self.vel * dt
        self.vel.y += 500 * dt  # Gravity
        self.life -= dt * 2
        self.size *= 0.98
        return self.life > 0

class Ball:
    """Ball entity with physics and effects."""
    __slots__ = ['pos', 'vel', 'radius', 'trail', 'speed_multiplier']

    def __init__(self, x: float, y: float):
        self.pos = Vector2D(x, y)
        self.vel = Vector2D(random.choice([-200, 200]), -300)
        self.radius = 8
        self.trail = []
        self.speed_multiplier = 1.0

    def update(self, dt: float, width: int, height: int):
        """Update ball position with boundary collision."""
        movement = self.vel * (dt * self.speed_multiplier)
        self.pos = self.pos + movement
        # Trail effect
        self.trail.append((self.pos.x, self.pos.y))
        self.trail = self.trail[-10:]  # Keep last 10 positions
        # Boundary collisions
        collision_handlers = {
            self.pos.x - self.radius <= 0: lambda: setattr(self.vel, 'x', abs(self.vel.x)),
            self.pos.x + self.radius >= width: lambda: setattr(self.vel, 'x', -abs(self.vel.x)),
            self.pos.y - self.radius <= 0: lambda: setattr(self.vel, 'y', abs(self.vel.y))
        }
        [handler() for condition, handler in collision_handlers.items() if condition]
        return self.pos.y > height  # Returns True if ball is lost

    def draw(self, surface: pygame.Surface):
        """Draw ball with trail effect."""
        # Draw trail
        trail_surface = pygame.Surface((surface.get_width(), surface.get_height()), pygame.SRCALPHA)
        for i, pos in enumerate(self.trail):
            alpha = int(100 * (i / len(self.trail)))
            color = (*ColorScheme.BALL_TRAIL[:3], alpha)
            pygame.draw.circle(trail_surface, color, (int(pos[0]), int(pos[1])),
                               self.radius * (0.5 + 0.5 * i / len(self.trail)))
        surface.blit(trail_surface, (0, 0))
        # Draw ball with glow
        glow_surf = pygame.Surface((self.radius * 4, self.radius * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*ColorScheme.BALL, 50),
                           (self.radius * 2, self.radius * 2), self.radius * 2)
        surface.blit(glow_surf, (self.pos.x - self.radius * 2, self.pos.y - self.radius * 2))
        # Draw main ball
        pygame.draw.circle(surface, ColorScheme.BALL,
                           (int(self.pos.x), int(self.pos.y)), self.radius)

class Paddle:
    """Player-controlled paddle with smooth movement."""
    __slots__ = ['x', 'y', 'width', 'height', 'base_width', 'vel', 'sticky']

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.base_width = 100
        self.width = self.base_width
        self.height = 20
        self.vel = 0
        self.sticky = False

    def update(self, dt: float, mouse_x: int, width: int):
        """Smooth paddle movement following mouse."""
        # Calculate velocity based on distance to target
        target_x = mouse_x - self.width // 2
        distance = target_x - self.x
        self.vel = distance * 10  # Proportional velocity
        # Update position
        self.x += self.vel * dt
        # Clamp to boundaries
        self.x = max(0, min(self.x, width - self.width))

    def draw(self, surface: pygame.Surface):
        """Draw paddle with gradient and glow effect."""
        # Glow effect
        glow_rect = pygame.Rect(self.x - 5, self.y - 3, self.width + 10, self.height + 6)
        glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, (*ColorScheme.PADDLE_GLOW, 100),
                         (0, 0, glow_rect.width, glow_rect.height), border_radius=10)
        surface.blit(glow_surf, glow_rect)
        # Main paddle with gradient
        paddle_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        pygame.draw.rect(surface, ColorScheme.PADDLE, paddle_rect, border_radius=8)
        # Highlight
        highlight_rect = pygame.Rect(self.x + 5, self.y + 2, self.width - 10, 5)
        pygame.draw.rect(surface, (*ColorScheme.PADDLE_GLOW, 150), highlight_rect, border_radius=3)

    def get_collision_normal(self, ball_x: float) -> Vector2D:
        """Calculate collision normal based on hit position."""
        relative_pos = (ball_x - (self.x + self.width / 2)) / (self.width / 2)
        relative_pos = max(-1, min(1, relative_pos))
        angle = relative_pos * math.pi / 3  # Max 60 degree angle
        return Vector2D(math.sin(angle), -math.cos(angle))

class Brick:
    """Brick entity with health and effects."""
    __slots__ = ['x', 'y', 'width', 'height', 'health', 'max_health', 'points', 'powerup']

    def __init__(self, x: float, y: float, health: int = 1):
        self.x = x
        self.y = y
        self.width = 75
        self.height = 25
        self.health = health
        self.max_health = health
        self.points = health * 100
        self.powerup = PowerUpType(random.randint(1, 6)) if random.random() < 0.1 else None

    def hit(self) -> bool:
        """Handle brick hit, return True if destroyed."""
        self.health -= 1
        return self.health <= 0

    def draw(self, surface: pygame.Surface):
        """Draw brick with gradient and damage effect."""
        color = ColorScheme.BRICK_COLORS.get(self.max_health, (200, 200, 200))
        # Damage effect
        damage_ratio = self.health / self.max_health
        adjusted_color = tuple(int(c * (0.5 + 0.5 * damage_ratio)) for c in color)
        # Draw brick with gradient
        rect = pygame.Rect(self.x, self.y, self.width, self.height)
        pygame.draw.rect(surface, adjusted_color, rect, border_radius=4)
        # Highlight
        highlight = pygame.Rect(self.x + 2, self.y + 2, self.width - 4, 8)
        highlight_color = tuple(min(255, c + 50) for c in adjusted_color)
        pygame.draw.rect(surface, highlight_color, highlight, border_radius=2)
        # Power-up indicator
        if self.powerup:
            pygame.draw.circle(surface, (255, 255, 100),
                               (self.x + self.width // 2, self.y + self.height // 2), 5)

class PowerUp:
    """Power-up entity that falls from destroyed bricks."""
    __slots__ = ['pos', 'type', 'vel', 'size', 'active']

    def __init__(self, x: float, y: float, powerup_type: PowerUpType):
        self.pos = Vector2D(x, y)
        self.type = powerup_type
        self.vel = Vector2D(0, 150)
        self.size = 20
        self.active = True

    def update(self, dt: float, height: int):
        """Update power-up position."""
        self.pos = self.pos + self.vel * dt
        return self.pos.y > height

    def draw(self, surface: pygame.Surface):
        """Draw power-up with pulsing effect."""
        pulse = abs(math.sin(pygame.time.get_ticks() * 0.005)) * 0.3 + 0.7
        size = int(self.size * pulse)
        colors = {
            PowerUpType.EXPAND_PADDLE: (100, 255, 100),
            PowerUpType.MULTI_BALL: (255, 100, 255),
            PowerUpType.SLOW_BALL: (100, 100, 255),
            PowerUpType.LASER: (255, 100, 100),
            PowerUpType.STICKY_PADDLE: (255, 255, 100),
            PowerUpType.EXTRA_LIFE: (255, 200, 200)
        }
        color = colors.get(self.type, (200, 200, 200))
        pygame.draw.circle(surface, color, (int(self.pos.x), int(self.pos.y)), size)
        pygame.draw.circle(surface, (255, 255, 255),
                           (int(self.pos.x), int(self.pos.y)), size, 2)

class ArkanoidGame:
    """Main game engine class with event-driven architecture."""

    def __init__(self, width: int = 800, height: int = 600):
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Modern Arkanoid - Professional Edition")
        self.clock = pygame.time.Clock()
        self.font_large = pygame.font.Font(None, 72)
        self.font_medium = pygame.font.Font(None, 36)
        self.font_small = pygame.font.Font(None, 24)
        self.state = GameState.MENU
        self.score = 0
        self.lives = 3
        self.level = 1
        self.paddle = Paddle(width // 2 - 50, height - 50)
        self.balls = [Ball(width // 2, height - 80)]
        self.bricks = []
        self.particles = []
        self.powerups = []
        self.state_handlers = {
            GameState.MENU: self._handle_menu,
            GameState.PLAYING: self._handle_playing,
            GameState.PAUSED: self._handle_paused,
            GameState.GAME_OVER: self._handle_game_over,
            GameState.VICTORY: self._handle_victory
        }
        self._generate_level(self.level)

    def _generate_level(self, level: int):
        """Generate brick layout for the level."""
        rows = min(5 + level, 10)
        cols = 10
        self.bricks = [
            Brick(x * 78 + 10, y * 30 + 60, min((rows - y), 5))
            for y in range(rows)
            for x in range(cols)
            if random.random() > 0.1  # 10% chance of missing brick
        ]

    def _create_gradient_background(self) -> pygame.Surface:
        """Create gradient background surface."""
        surf = pygame.Surface((self.width, self.height))
        for y in range(self.height):
            ratio = y / self.height
            color = tuple(int(c1 * (1 - ratio) + c2 * ratio)
                          for c1, c2 in zip(ColorScheme.BACKGROUND_TOP, ColorScheme.BACKGROUND_BOTTOM))
            pygame.draw.line(surf, color, (0, y), (self.width, y))
        return surf

    def _handle_collision(self, ball: Ball, dt: float):
        """Handle ball collisions with game objects."""
        # Paddle collision
        paddle_rect = pygame.Rect(self.paddle.x, self.paddle.y, self.paddle.width, self.paddle.height)
        ball_rect = pygame.Rect(ball.pos.x - ball.radius, ball.pos.y - ball.radius,
                                ball.radius * 2, ball.radius * 2)
        if paddle_rect.colliderect(ball_rect) and ball.vel.y > 0:
            normal = self.paddle.get_collision_normal(ball.pos.x)
            ball.vel = ball.vel.reflect(normal)
            ball.vel = ball.vel.normalize() * ball.vel.magnitude
            ball.pos.y = self.paddle.y - ball.radius
            # Add paddle velocity influence
            ball.vel.x += self.paddle.vel * 0.3
            # Create particles
            self._create_particles(ball.pos.x, ball.pos.y, 5)
        # Brick collisions
        for brick in self.bricks[:]:
            brick_rect = pygame.Rect(brick.x, brick.y, brick.width, brick.height)
            if brick_rect.colliderect(ball_rect):
                if brick.hit():
                    self.bricks.remove(brick)
                    self.score += brick.points
                    self._create_particles(brick.x + brick.width // 2,
                                           brick.y + brick.height // 2, 10)
                    # Create power-up
                    if brick.powerup:
                        self.powerups.append(PowerUp(brick.x + brick.width // 2,
                                                     brick.y + brick.height // 2,
                                                     brick.powerup))
                # Calculate bounce direction
                ball_center_x = ball.pos.x
                ball_center_y = ball.pos.y
                brick_center_x = brick.x + brick.width // 2
                brick_center_y = brick.y + brick.height // 2
                diff_x = ball_center_x - brick_center_x
                diff_y = ball_center_y - brick_center_y
                if abs(diff_x) > abs(diff_y):
                    ball.vel.x = -ball.vel.x
                else:
                    ball.vel.y = -ball.vel.y
                break

    def _create_particles(self, x: float, y: float, count: int):
        """Create particle effects."""
        velocities = [
            Vector2D(random.uniform(-200, 200), random.uniform(-300, -100))
            for _ in range(count)
        ]
        self.particles.extend([Particle(x, y, vel, ColorScheme.PARTICLE) for vel in velocities])

    def _handle_powerups(self, dt: float):
        """Handle power-up collection and effects."""
        paddle_rect = pygame.Rect(self.paddle.x, self.paddle.y, self.paddle.width, self.paddle.height)
        for powerup in self.powerups[:]:
            if powerup.update(dt, self.height):
                self.powerups.remove(powerup)
                continue
            powerup_rect = pygame.Rect(powerup.pos.x - powerup.size,
                                       powerup.pos.y - powerup.size,
                                       powerup.size * 2, powerup.size * 2)
            if paddle_rect.colliderect(powerup_rect):
                self._apply_powerup(powerup.type)
                self.powerups.remove(powerup)
                self._create_particles(powerup.pos.x, powerup.pos.y, 15)

    def _apply_powerup(self, powerup_type: PowerUpType):
        """Apply power-up effect."""
        effects = {
            PowerUpType.EXPAND_PADDLE: lambda: setattr(self.paddle, 'width',
                                                       min(self.paddle.width + 30, 200)),
            PowerUpType.MULTI_BALL: lambda: self.balls.extend([
                Ball(self.balls[0].pos.x, self.balls[0].pos.y) for _ in range(2)
            ]) if self.balls else None,
            PowerUpType.SLOW_BALL: lambda: [setattr(ball, 'speed_multiplier', 0.7)
                                            for ball in self.balls],
            PowerUpType.STICKY_PADDLE: lambda: setattr(self.paddle, 'sticky', True),
            PowerUpType.EXTRA_LIFE: lambda: setattr(self, 'lives', self.lives + 1),
        }
        effect = effects.get(powerup_type)
        if effect:
            effect()
        self.score += 50

    def _handle_menu(self, dt: float, events: List[pygame.event.Event]):
        """Handle menu state."""
        # Draw gradient background
        background = self._create_gradient_background()
        self.screen.blit(background, (0, 0))
        # Title with shadow
        title = self.font_large.render("ARKANOID", True, ColorScheme.TEXT_PRIMARY)
        shadow = self.font_large.render("ARKANOID", True, ColorScheme.TEXT_SHADOW)
        title_rect = title.get_rect(center=(self.width // 2, 150))
        self.screen.blit(shadow, (title_rect.x + 3, title_rect.y + 3))
        self.screen.blit(title, title_rect)
        # Subtitle
        subtitle = self.font_small.render("Professional Edition", True, ColorScheme.TEXT_SECONDARY)
        subtitle_rect = subtitle.get_rect(center=(self.width // 2, 200))
        self.screen.blit(subtitle, subtitle_rect)
        # Instructions
        instructions = [
            "Click to Start",
            "Move mouse to control paddle",
            "ESC to pause"
        ]
        for i, text in enumerate(instructions):
            inst = self.font_medium.render(text, True, ColorScheme.TEXT_PRIMARY)
            inst_rect = inst.get_rect(center=(self.width // 2, 300 + i * 50))
            self.screen.blit(inst, inst_rect)
        # Check for start
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.state = GameState.PLAYING
                self._generate_level(self.level)

    def _handle_playing(self, dt: float, events: List[pygame.event.Event]):
        """Handle playing state."""
        # Update game objects
        mouse_x, _ = pygame.mouse.get_pos()
        self.paddle.update(dt, mouse_x, self.width)
        # Update balls
        for ball in self.balls[:]:
            if ball.update(dt, self.width, self.height):
                self.balls.remove(ball)
                if not self.balls:
                    self.lives -= 1
                    if self.lives > 0:
                        self.balls = [Ball(self.width // 2, self.height - 80)]
                    else:
                        self.state = GameState.GAME_OVER
            else:
                self._handle_collision(ball, dt)
        # Update particles
        self.particles = [p for p in self.particles if p.update(dt)]
        # Update power-ups
        self._handle_powerups(dt)
        # Check victory
        if not self.bricks:
            self.level += 1
            if self.level > 5:
                self.state = GameState.VICTORY
            else:
                self._generate_level(self.level)
                self.balls = [Ball(self.width // 2, self.height - 80)]
        # Check pause
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.state = GameState.PAUSED
        # Draw everything
        self._draw_game()

    def _handle_paused(self, dt: float, events: List[pygame.event.Event]):
        """Handle paused state."""
        self._draw_game()
        # Draw pause overlay
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.screen.blit(overlay, (0, 0))
        pause_text = self.font_large.render("PAUSED", True, ColorScheme.TEXT_PRIMARY)
        pause_rect = pause_text.get_rect(center=(self.width // 2, self.height // 2))
        self.screen.blit(pause_text, pause_rect)
        resume_text = self.font_medium.render("Press ESC to Resume", True, ColorScheme.TEXT_SECONDARY)
        resume_rect = resume_text.get_rect(center=(self.width // 2, self.height // 2 + 60))
        self.screen.blit(resume_text, resume_rect)
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.state = GameState.PLAYING

    def _handle_game_over(self, dt: float, events: List[pygame.event.Event]):
        """Handle game over state."""
        background = self._create_gradient_background()
        self.screen.blit(background, (0, 0))
        game_over_text = self.font_large.render("GAME OVER", True, ColorScheme.TEXT_PRIMARY)
        game_over_rect = game_over_text.get_rect(center=(self.width // 2, self.height // 2 - 50))
        self.screen.blit(game_over_text, game_over_rect)
        score_text = self.font_medium.render(f"Final Score: {self.score}", True, ColorScheme.TEXT_SECONDARY)
        score_rect = score_text.get_rect(center=(self.width // 2, self.height // 2 + 20))
        self.screen.blit(score_text, score_rect)
        restart_text = self.font_medium.render("Click to Restart", True, ColorScheme.TEXT_PRIMARY)
        restart_rect = restart_text.get_rect(center=(self.width // 2, self.height // 2 + 80))
        self.screen.blit(restart_text, restart_rect)
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.__init__(self.width, self.height)

    def _handle_victory(self, dt: float, events: List[pygame.event.Event]):
        """Handle victory state."""
        background = self._create_gradient_background()
        self.screen.blit(background, (0, 0))
        victory_text = self.font_large.render("VICTORY!", True, ColorScheme.TEXT_PRIMARY)
        victory_rect = victory_text.get_rect(center=(self.width // 2, self.height // 2 - 50))
        self.screen.blit(victory_text, victory_rect)
        score_text = self.font_medium.render(f"Final Score: {self.score}", True, ColorScheme.TEXT_SECONDARY)
        score_rect = score_text.get_rect(center=(self.width // 2, self.height // 2 + 20))
        self.screen.blit(score_text, score_rect)
        restart_text = self.font_medium.render("Click to Play Again", True, ColorScheme.TEXT_PRIMARY)
        restart_rect = restart_text.get_rect(center=(self.width // 2, self.height // 2 + 80))
        self.screen.blit(restart_text, restart_rect)
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.__init__(self.width, self.height)

    def _draw_game(self):
        """Draw the game scene."""
        # Background
        background = self._create_gradient_background()
        self.screen.blit(background, (0, 0))
        # Draw bricks
        for brick in self.bricks:
            brick.draw(self.screen)
        # Draw power-ups
        for powerup in self.powerups:
            powerup.draw(self.screen)
        # Draw particles
        particle_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        for particle in self.particles:
            alpha = int(200 * particle.life)
            color = (*particle.color[:3], alpha)
            pygame.draw.circle(particle_surf, color,
                               (int(particle.pos.x), int(particle.pos.y)), int(particle.size))
        self.screen.blit(particle_surf, (0, 0))
        # Draw paddle
        self.paddle.draw(self.screen)
        # Draw balls
        for ball in self.balls:
            ball.draw(self.screen)
        # Draw UI
        self._draw_ui()

    def _draw_ui(self):
        """Draw user interface elements."""
        # Score
        score_text = self.font_medium.render(f"Score: {self.score}", True, ColorScheme.TEXT_PRIMARY)
        self.screen.blit(score_text, (10, 10))
        # Lives
        lives_text = self.font_medium.render(f"Lives: {self.lives}", True, ColorScheme.TEXT_PRIMARY)
        self.screen.blit(lives_text, (self.width - 120, 10))
        # Level
        level_text = self.font_medium.render(f"Level: {self.level}", True, ColorScheme.TEXT_PRIMARY)
        level_rect = level_text.get_rect(center=(self.width // 2, 25))
        self.screen.blit(level_text, level_rect)

    def run(self):
        """Main game loop with event-driven architecture."""
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0  # 60 FPS
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    running = False
            # Delegate to state handler
            handler = self.state_handlers.get(self.state)
            if handler:
                handler(dt, events)
            pygame.display.flip()
        pygame.quit()

def main():
    """Entry point for the application."""
    game = ArkanoidGame()
    game.run()

if __name__ == "__main__":
    main()
