#!/usr/bin/env python3
"""
Test suite for Arkanoid game components
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch
import pygame

# Add the game directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from arkanoid import (
    Vector2D, Ball, Paddle, Brick, PowerUp, Particle,
    GameState, PowerUpType, ArkanoidGame
)


class TestVector2D(unittest.TestCase):
    """Test Vector2D mathematical operations."""
    
    def test_vector_creation(self):
        v = Vector2D(3, 4)
        self.assertEqual(v.x, 3)
        self.assertEqual(v.y, 4)
    
    def test_vector_addition(self):
        v1 = Vector2D(1, 2)
        v2 = Vector2D(3, 4)
        result = v1 + v2
        self.assertEqual(result.x, 4)
        self.assertEqual(result.y, 6)
    
    def test_vector_multiplication(self):
        v = Vector2D(2, 3)
        result = v * 2
        self.assertEqual(result.x, 4)
        self.assertEqual(result.y, 6)
    
    def test_vector_magnitude(self):
        v = Vector2D(3, 4)
        self.assertEqual(v.magnitude, 5.0)
    
    def test_vector_normalize(self):
        v = Vector2D(3, 4)
        normalized = v.normalize()
        self.assertAlmostEqual(normalized.magnitude, 1.0, places=5)
    
    def test_vector_reflect(self):
        v = Vector2D(1, -1)
        normal = Vector2D(0, 1)
        reflected = v.reflect(normal)
        self.assertEqual(reflected.x, 1)
        self.assertEqual(reflected.y, 1)


class TestBall(unittest.TestCase):
    """Test Ball physics and behavior."""
    
    def setUp(self):
        pygame.init()
        
    def test_ball_creation(self):
        ball = Ball(400, 300)
        self.assertEqual(ball.pos.x, 400)
        self.assertEqual(ball.pos.y, 300)
        self.assertEqual(ball.radius, 8)
        self.assertEqual(ball.speed_multiplier, 1.0)
    
    def test_ball_update_movement(self):
        ball = Ball(400, 300)
        ball.vel = Vector2D(100, 0)  # Moving right
        ball.update(0.1, 800, 600)  # 0.1 second update
        self.assertAlmostEqual(ball.pos.x, 410, places=1)
    
    def test_ball_boundary_collision_left(self):
        ball = Ball(10, 300)
        ball.vel = Vector2D(-100, 0)  # Moving left
        ball.update(0.1, 800, 600)
        self.assertTrue(ball.vel.x > 0)  # Should bounce right
    
    def test_ball_boundary_collision_right(self):
        ball = Ball(790, 300)
        ball.vel = Vector2D(100, 0)  # Moving right
        ball.update(0.1, 800, 600)
        self.assertTrue(ball.vel.x < 0)  # Should bounce left
    
    def test_ball_lost_detection(self):
        ball = Ball(400, 595)
        ball.vel = Vector2D(0, 100)  # Moving down
        lost = ball.update(0.1, 800, 600)
        self.assertTrue(lost)


class TestPaddle(unittest.TestCase):
    """Test Paddle movement and collision."""
    
    def setUp(self):
        pygame.init()
    
    def test_paddle_creation(self):
        paddle = Paddle(350, 550)
        self.assertEqual(paddle.x, 350)
        self.assertEqual(paddle.y, 550)
        self.assertEqual(paddle.width, paddle.base_width)
        self.assertEqual(paddle.base_width, 100)
    def test_paddle_movement(self):
        paddle = Paddle(350, 550)
        paddle.update(0.1, 500, 800)  # Move to mouse position (center target=500)
        self.assertNotEqual(paddle.x, 350)  # Should have moved
    
    def test_paddle_boundary_limits(self):
        paddle = Paddle(0, 550)
        paddle.update(0.1, -100, 800)  # Try to move beyond left boundary
        self.assertGreaterEqual(paddle.x, 0)
        
        paddle.x = 700
        paddle.update(0.1, 900, 800)  # Try to move beyond right boundary
        self.assertLessEqual(paddle.x, 800 - paddle.width)
    
    def test_collision_normal_calculation(self):
        paddle = Paddle(350, 550)
        
        # Ball hits center
        normal_center = paddle.get_collision_normal(400)
        self.assertAlmostEqual(normal_center.x, 0, places=2)
        
        # Ball hits left edge
        normal_left = paddle.get_collision_normal(350)
        self.assertTrue(normal_left.x < 0)
        
        # Ball hits right edge
        normal_right = paddle.get_collision_normal(450)
        self.assertTrue(normal_right.x > 0)


class TestBrick(unittest.TestCase):
    """Test Brick health and destruction."""
    
    def test_brick_creation(self):
        brick = Brick(100, 50, health=3)
        self.assertEqual(brick.x, 100)
        self.assertEqual(brick.y, 50)
        self.assertEqual(brick.health, 3)
        self.assertEqual(brick.max_health, 3)
        self.assertEqual(brick.points, 300)
    
    def test_brick_hit(self):
        brick = Brick(100, 50, health=2)
        destroyed = brick.hit()
        self.assertEqual(brick.health, 1)
        self.assertFalse(destroyed)
        
        destroyed = brick.hit()
        self.assertEqual(brick.health, 0)
        self.assertTrue(destroyed)
    
    def test_brick_powerup_chance(self):
        # Test that power-ups are sometimes created
        has_powerup = False
        for _ in range(100):
            brick = Brick(100, 50)
            if brick.powerup is not None:
                has_powerup = True
                break
        self.assertTrue(has_powerup, "No power-ups generated in 100 attempts")


class TestPowerUp(unittest.TestCase):
    """Test PowerUp behavior."""
    
    def test_powerup_creation(self):
        powerup = PowerUp(400, 100, PowerUpType.EXTRA_LIFE)
        self.assertEqual(powerup.pos.x, 400)
        self.assertEqual(powerup.pos.y, 100)
        self.assertEqual(powerup.type, PowerUpType.EXTRA_LIFE)
        self.assertTrue(powerup.active)
    
    def test_powerup_falling(self):
        powerup = PowerUp(400, 100, PowerUpType.MULTI_BALL)
        initial_y = powerup.pos.y
        powerup.update(0.1, 600)
        self.assertGreater(powerup.pos.y, initial_y)
    
    def test_powerup_out_of_bounds(self):
        powerup = PowerUp(400, 590, PowerUpType.SLOW_BALL)
        out = powerup.update(0.1, 600)
        self.assertTrue(out)


class TestParticle(unittest.TestCase):
    """Test Particle effects."""
    
    def test_particle_creation(self):
        vel = Vector2D(50, -100)
        particle = Particle(200, 300, vel, (255, 255, 255))
        self.assertEqual(particle.pos.x, 200)
        self.assertEqual(particle.pos.y, 300)
        self.assertEqual(particle.life, 1.0)
    
    def test_particle_update(self):
        vel = Vector2D(0, 0)
        particle = Particle(200, 300, vel, (255, 255, 255))
        initial_life = particle.life
        alive = particle.update(0.1)
        
        self.assertLess(particle.life, initial_life)
        self.assertTrue(alive)  # Still alive after first update
        
        # Simulate many updates
        for _ in range(20):
            alive = particle.update(0.1)
        self.assertFalse(alive)  # Should be dead after many updates


class TestGameStates(unittest.TestCase):
    """Test game state transitions."""
    
    def test_game_state_enum(self):
        self.assertEqual(GameState.MENU.value, 1)
        self.assertEqual(GameState.PLAYING.value, 2)
        self.assertEqual(GameState.PAUSED.value, 3)
        self.assertEqual(GameState.GAME_OVER.value, 4)
        self.assertEqual(GameState.VICTORY.value, 5)
    
    def test_powerup_type_enum(self):
        self.assertEqual(PowerUpType.EXPAND_PADDLE.value, 1)
        self.assertEqual(PowerUpType.MULTI_BALL.value, 2)
        self.assertEqual(PowerUpType.SLOW_BALL.value, 3)
        self.assertEqual(PowerUpType.LASER.value, 4)
        self.assertEqual(PowerUpType.STICKY_PADDLE.value, 5)
        self.assertEqual(PowerUpType.EXTRA_LIFE.value, 6)


class TestArkanoidGame(unittest.TestCase):
    """Test main game engine."""
    
    @patch('pygame.display.set_mode')
    @patch('pygame.font.Font')
    def setUp(self, mock_font, mock_display):
        pygame.init()
        mock_display.return_value = Mock()
        mock_font.return_value = Mock()
        self.game = ArkanoidGame(800, 600)
    
    def test_game_initialization(self):
        self.assertEqual(self.game.width, 800)
        self.assertEqual(self.game.height, 600)
        self.assertEqual(self.game.state, GameState.MENU)
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.level, 1)
        self.assertIsNotNone(self.game.paddle)
        self.assertEqual(len(self.game.balls), 1)
    
    def test_level_generation(self):
        initial_bricks = len(self.game.bricks)
        self.assertGreater(initial_bricks, 0)
        
        # Generate level 2
        self.game._generate_level(2)
        level2_bricks = len(self.game.bricks)
        self.assertGreater(level2_bricks, 0)
    
    def test_particle_creation(self):
        initial_particles = len(self.game.particles)
        self.game._create_particles(400, 300, 5)
        self.assertEqual(len(self.game.particles), initial_particles + 5)
    
    def test_powerup_application(self):
        initial_lives = self.game.lives
        self.game._apply_powerup(PowerUpType.EXTRA_LIFE)
        self.assertEqual(self.game.lives, initial_lives + 1)
        
        initial_width = self.game.paddle.width
        self.game._apply_powerup(PowerUpType.EXPAND_PADDLE)
        self.assertGreater(self.game.paddle.width, initial_width)
        
        initial_balls = len(self.game.balls)
        self.game._apply_powerup(PowerUpType.MULTI_BALL)
        self.assertGreater(len(self.game.balls), initial_balls)
    
    def test_state_handlers_exist(self):
        for state in GameState:
            self.assertIn(state, self.game.state_handlers)
            self.assertIsNotNone(self.game.state_handlers[state])


def run_tests():
    """Run all tests."""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == "__main__":
    print("=" * 60)
    print("Running Arkanoid Game Test Suite")
    print("=" * 60)
    run_tests()
    print("=" * 60)
    print("Test suite completed!")
    print("=" * 60)