import math
import random
import pygame

from .target import Target


# Colors
WHITE = (255, 255, 255)
RED = (220, 60, 60)
GREEN = (70, 220, 100)
BLUE = (80, 150, 240)
DARK_GRAY = (35, 35, 40)
YELLOW = (240, 210, 70)


class GameEngine:
    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.margin = 60
        self.hud_height = 60

        # Round duration
        self.round_seconds = 30

        # Difficulty settings
        # lifespan is measured in frames at 60 FPS
        self.difficulties = {
            "Easy": {
                "radius": 45,
                "min_radius": 18,
                "lifespan": 120,
            },
            "Medium": {
                "radius": 40,
                "min_radius": 12,
                "lifespan": 90,
            },
            "Hard": {
                "radius": 35,
                "min_radius": 8,
                "lifespan": 60,
            },
        }

        self.difficulty = "Medium"

        self.font = pygame.font.SysFont("Arial", 26)
        self.small_font = pygame.font.SysFont("Arial", 22)
        self.big_font = pygame.font.SysFont("Arial", 52)

        # Initialize sound system.
        # Sound effects are generated programmatically, so no external
        # audio files are required.
        self.sound_enabled = False
        self.sound_hit = None
        self.sound_miss = None
        self.sound_game_over = None

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()

            self.sound_hit = self._create_sound(800, 0.08)
            self.sound_miss = self._create_sound(250, 0.12)
            self.sound_game_over = self._create_sound(450, 0.35)

            self.sound_enabled = True
        except pygame.error:
            # The game can still run if audio is unavailable.
            self.sound_enabled = False

        self.state = "playing"

        self.start_round()

    # ---------------------------------------------------------
    # SOUND
    # ---------------------------------------------------------

    def _create_sound(self, frequency, duration):
        """Create a simple beep sound without needing an audio file."""

        sample_rate = 44100
        samples = int(sample_rate * duration)

        sound_buffer = bytearray()

        for i in range(samples):
            value = int(
                32767
                * 0.25
                * math.sin(
                    2 * math.pi * frequency * i / sample_rate
                )
            )

            packed_value = value.to_bytes(
                2,
                byteorder="little",
                signed=True,
            )

            # Stereo: left + right
            sound_buffer.extend(packed_value)
            sound_buffer.extend(packed_value)

        return pygame.mixer.Sound(buffer=bytes(sound_buffer))

    def _play_sound(self, sound):
        if self.sound_enabled and sound is not None:
            sound.play()

    # ---------------------------------------------------------
    # ROUND MANAGEMENT
    # ---------------------------------------------------------

    def start_round(self):
        """Start a new round using the currently selected difficulty."""

        settings = self.difficulties[self.difficulty]

        self.time_left_frames = self.round_seconds * 60

        self.hits = 0
        self.misses = 0
        self.score = 0

        self.game_over = False
        self.state = "playing"

        self.target = self._spawn_target()

    def _spawn_target(self):
        """Create a new target using the selected difficulty."""

        settings = self.difficulties[self.difficulty]

        radius = settings["radius"]

        # Keep the complete target inside the playable area.
        x = random.randint(
            self.margin + radius,
            self.width - self.margin - radius,
        )

        y = random.randint(
            self.margin + self.hud_height + radius,
            self.height - self.margin - radius,
        )

        return Target(
            x,
            y,
            base_radius=settings["radius"],
            min_radius=settings["min_radius"],
            lifespan_frames=settings["lifespan"],
        )

    # ---------------------------------------------------------
    # INPUT
    # ---------------------------------------------------------

    def handle_event(self, event):

        # Game Over screen
        if self.state == "game_over":

            if event.type == pygame.KEYDOWN:

                # Easy
                if event.key == pygame.K_e:
                    self.difficulty = "Easy"
                    self.start_round()

                # Medium
                elif event.key == pygame.K_m:
                    self.difficulty = "Medium"
                    self.start_round()

                # Hard
                elif event.key == pygame.K_h:
                    self.difficulty = "Hard"
                    self.start_round()

                # Exit
                elif event.key == pygame.K_ESCAPE:
                    self.state = "exit"

            return

        # Normal gameplay
        if event.type == pygame.MOUSEBUTTONDOWN:
            self._handle_click(event.pos)

    def _handle_click(self, pos):

        if self.state != "playing":
            return

        x, y = pos

        if self.target.contains_point(x, y):

            # Successful hit
            self.hits += 1
            self.score += 1

            self._play_sound(self.sound_hit)

            # Immediately create a new target
            self.target = self._spawn_target()

        else:

            # Miss
            self.misses += 1

            self._play_sound(self.sound_miss)

    def handle_input(self):
        # Reserved for keyboard input if needed later.
        pass

    # ---------------------------------------------------------
    # UPDATE
    # ---------------------------------------------------------

    def update(self):

        if self.state != "playing":
            return

        # Countdown
        self.time_left_frames -= 1

        # Round finished
        if self.time_left_frames <= 0:

            self.game_over = True
            self.state = "game_over"

            self._play_sound(self.sound_game_over)

            return

        # Update target
        self.target.update()

        # Target timed out
        if self.target.expired():

            self.misses += 1

            self._play_sound(self.sound_miss)

            self.target = self._spawn_target()

    # ---------------------------------------------------------
    # STATISTICS
    # ---------------------------------------------------------

    def accuracy(self):

        total = self.hits + self.misses

        if total == 0:
            return 0.0

        return round(
            100 * self.hits / total,
            1,
        )

    # ---------------------------------------------------------
    # RENDERING
    # ---------------------------------------------------------

    def render(self, screen):

        screen.fill(DARK_GRAY)

        # -----------------------------------------------------
        # GAMEPLAY SCREEN
        # -----------------------------------------------------

        if self.state == "playing":

            radius = int(
                self.target.visual_radius()
            )

            # Draw target
            pygame.draw.circle(
                screen,
                RED,
                (self.target.x, self.target.y),
                radius,
            )

            # Target outline
            pygame.draw.circle(
                screen,
                WHITE,
                (self.target.x, self.target.y),
                radius,
                2,
            )

            # Score
            score_text = self.font.render(
                f"Score: {self.score}",
                True,
                WHITE,
            )

            screen.blit(
                score_text,
                (10, 10),
            )

            # Timer
            seconds_left = max(
                0,
                self.time_left_frames // 60,
            )

            timer_text = self.font.render(
                f"Time: {seconds_left}s",
                True,
                WHITE,
            )

            screen.blit(
                timer_text,
                (self.width - 140, 10),
            )

            # Accuracy
            accuracy_text = self.font.render(
                f"Accuracy: {self.accuracy()}%",
                True,
                WHITE,
            )

            screen.blit(
                accuracy_text,
                (self.width // 2 - 90, 10),
            )

            # Difficulty
            difficulty_text = self.small_font.render(
                f"Difficulty: {self.difficulty}",
                True,
                YELLOW,
            )

            screen.blit(
                difficulty_text,
                (10, self.height - 35),
            )

        # -----------------------------------------------------
        # GAME OVER SCREEN
        # -----------------------------------------------------

        elif self.state == "game_over":

            # Title
            title = self.big_font.render(
                "GAME OVER",
                True,
                RED,
            )

            screen.blit(
                title,
                (
                    self.width // 2
                    - title.get_width() // 2,
                    70,
                ),
            )

            # Final score
            score_text = self.font.render(
                f"Final Score: {self.score}",
                True,
                WHITE,
            )

            screen.blit(
                score_text,
                (
                    self.width // 2
                    - score_text.get_width() // 2,
                    150,
                ),
            )

            # Final accuracy
            accuracy_text = self.font.render(
                f"Accuracy: {self.accuracy()}%",
                True,
                WHITE,
            )

            screen.blit(
                accuracy_text,
                (
                    self.width // 2
                    - accuracy_text.get_width() // 2,
                    195,
                ),
            )

            # Hits / misses
            stats_text = self.small_font.render(
                f"Hits: {self.hits}    Misses: {self.misses}",
                True,
                WHITE,
            )

            screen.blit(
                stats_text,
                (
                    self.width // 2
                    - stats_text.get_width() // 2,
                    240,
                ),
            )

            # Current difficulty
            difficulty_text = self.small_font.render(
                f"Current Difficulty: {self.difficulty}",
                True,
                YELLOW,
            )

            screen.blit(
                difficulty_text,
                (
                    self.width // 2
                    - difficulty_text.get_width() // 2,
                    280,
                ),
            )

            # Replay instructions
            replay_text = self.small_font.render(
                "E = Easy     M = Medium     H = Hard",
                True,
                GREEN,
            )

            screen.blit(
                replay_text,
                (
                    self.width // 2
                    - replay_text.get_width() // 2,
                    350,
                ),
            )

            # Exit instruction
            exit_text = self.small_font.render(
                "ESC = Exit",
                True,
                BLUE,
            )

            screen.blit(
                exit_text,
                (
                    self.width // 2
                    - exit_text.get_width() // 2,
                    395,
                ),
            )