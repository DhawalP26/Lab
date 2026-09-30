import pygame
import random

TILE = 40
COLS, ROWS = 20, 15
WALL, FLOOR, CHEST, KEY, TRAP= 0, 1, 2, 3, 4
SPEED = 3

def generate_world():
    grid = [[WALL]*COLS for _ in range(ROWS)]
    rooms = []
    for _ in range(8):
        w = random.randint(3,6)
        h = random.randint(3,5)
        x = random.randint(1, COLS-w-1)
        y = random.randint(1, ROWS-h-1)
        room = pygame.Rect(x, y, w, h)
        overlap = any(room.inflate(2,2).colliderect(r) for r in rooms)
        if not overlap:
            rooms.append(room)
            for ry in range(y, y+h):
                for rx in range(x, x+w):
                    grid[ry][rx] = FLOOR

    for i in range(len(rooms)-1):
        ax, ay = rooms[i].centerx, rooms[i].centery
        bx, by = rooms[i+1].centerx, rooms[i+1].centery
        cx = ax
        while cx != bx:
            grid[ay][cx] = FLOOR
            cx += 1 if bx > cx else -1
        cy = ay
        while cy != by:
            grid[cy][bx] = FLOOR
            cy += 1 if by > cy else -1

    if len(rooms) >= 2:
        cr, ck = rooms[-1], rooms[-2]
        grid[cr.centery][cr.centerx] = CHEST
        grid[ck.centery][ck.centerx] = KEY

    start = rooms[0] if rooms else None
    return grid, start

COLORS = {
    WALL: (60,50,70),
    FLOOR: (200,190,170),
    CHEST: (200,160,30),
    KEY: (220,220,60),
    TRAP: (180, 50, 50),
}

class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 28, 28)
        self.color = (60,120,220)
        self.has_key = False

    def move(self, keys, grid, rows, cols):
        dx=dy=0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: dx=-SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx=SPEED
        if keys[pygame.K_UP] or keys[pygame.K_w]: dy=-SPEED
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: dy=SPEED
        self._try_move(dx,0,grid,rows,cols)
        self._try_move(0,dy,grid,rows,cols)

    def _try_move(self, dx, dy, grid, rows, cols):
        new = self.rect.move(dx,dy)
        for px,py in [(new.left,new.top),(new.right-1,new.top),(new.left,new.bottom-1),(new.right-1,new.bottom-1)]:
            c,r=px//TILE,py//TILE
            if not(0<=r<rows and 0<=c<cols) or grid[r][c]==WALL:
                return
        self.rect=new

    def draw(self, screen):
        pygame.draw.ellipse(screen, self.color, self.rect)
        if self.has_key:
            pygame.draw.circle(screen, (220,220,60), (self.rect.right-6, self.rect.top+6), 5)

class Guard:
    def __init__(self, x, y, patrol_start, patrol_end):
        self.rect = pygame.Rect(x, y, 28, 28)
        self.color = (180, 60, 60)

        self.patrol_start = patrol_start
        self.patrol_end = patrol_end
        self.target = patrol_end

        self.speed = 2

    def update(self):
        target_x, target_y = self.target

        dx = target_x - self.rect.x
        dy = target_y - self.rect.y

        if abs(dx) <= self.speed and abs(dy) <= self.speed:
            self.rect.topleft = self.target

            if self.target == self.patrol_end:
                self.target = self.patrol_start
            else:
                self.target = self.patrol_end
        else:
            if dx != 0:
                self.rect.x += self.speed if dx > 0 else -self.speed

            if dy != 0:
                self.rect.y += self.speed if dy > 0 else -self.speed

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect, border_radius=6)
        pygame.draw.circle(
            screen,
            (255, 220, 220),
            (self.rect.centerx - 5, self.rect.centery - 4),
            3
        )
        pygame.draw.circle(
            screen,
            (255, 220, 220),
            (self.rect.centerx + 5, self.rect.centery - 4),
            3
        )

WIDTH = COLS * TILE
HEIGHT = ROWS * TILE + 50
FPS = 60
MINIMAP_TILE = 8
MINIMAP_MARGIN = 10

class GameEngine:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Treasure Hunt")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 24)
        self.big_font = pygame.font.SysFont("monospace", 40, bold=True)
        self.reset()

    def find_path(self, start, target):
        from collections import deque

        queue = deque([start])
        parent = {start: None}

        while queue:
            r, c = queue.popleft()

            if (r, c) == target:
                path = []
                current = target

                while current is not None:
                    path.append(current)
                    current = parent[current]

                return path

            for dr, dc in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                nr = r + dr
                nc = c + dc

                if not (0 <= nr < ROWS and 0 <= nc < COLS):
                    continue

                if (nr, nc) in parent:
                    continue

                # Anything except a wall can be traversed.
                if self.grid[nr][nc] != WALL:
                    parent[(nr, nc)] = (r, c)
                    queue.append((nr, nc))

        return []

    def reset(self):
        self.grid, start = generate_world()
        if start:
            sx = start.x * TILE + 6
            sy = start.y * TILE + 6
        else:
            sx, sy = TILE+6, TILE+6
        self.start_pos = (sx, sy)
        self.player = Player(sx, sy)

        # Find the key and chest positions.
        key_pos = None
        chest_pos = None

        for r in range(ROWS):
            for c in range(COLS):
                if self.grid[r][c] == KEY:
                    key_pos = (r, c)
                elif self.grid[r][c] == CHEST:
                    chest_pos = (r, c)

        # Reserve a guaranteed path from start -> key -> chest.
        protected = set()

        if start and key_pos and chest_pos:
            start_cell = (start.y, start.x)

            path_to_key = self.find_path(start_cell, key_pos)
            path_to_chest = self.find_path(key_pos, chest_pos)

            protected.update(path_to_key)
            protected.update(path_to_chest)

        # Place traps only outside the guaranteed path.
        trap_count = 4
        placed = 0

        trap_candidates = []

        for r in range(ROWS):
            for c in range(COLS):
                if self.grid[r][c] == FLOOR:
                    if (r, c) not in protected:
                        if not (start and start.collidepoint(c, r)):
                            trap_candidates.append((r, c))

        random.shuffle(trap_candidates)

        for r, c in trap_candidates:
            if placed >= trap_count:
                break

            self.grid[r][c] = TRAP
            placed += 1
            # Create a guard near the chest.
        chest_pos = None

        for r in range(ROWS):
            for c in range(COLS):
                if self.grid[r][c] == CHEST:
                    chest_pos = (c, r)
                    break
            if chest_pos:
                break

        if chest_pos:
            chest_c, chest_r = chest_pos

            guard_x = chest_c * TILE + 6
            guard_y = chest_r * TILE + 6

            patrol_start = (guard_x - TILE, guard_y)
            patrol_end = (guard_x + TILE, guard_y)

            self.guard = Guard(
                guard_x,
                guard_y,
                patrol_start,
                patrol_end
            )
        else:
            self.guard = None
        self.won = False
        self.status = "Find the KEY, then the CHEST!"

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r: self.reset()
        return True

    def update(self):
        if self.won:
            return

        keys = pygame.key.get_pressed()
        self.player.move(keys, self.grid, ROWS, COLS)

        if self.guard:
            self.guard.update()

            if self.player.rect.colliderect(self.guard.rect):
                self.player.rect.topleft = self.start_pos
                self.status = "Guard caught you! Back to START!"
        pr = self.player.rect.centery // TILE
        pc = self.player.rect.centerx // TILE
        if 0<=pr<ROWS and 0<=pc<COLS:
            cell = self.grid[pr][pc]
            if cell == KEY:
                self.player.has_key = True
                self.grid[pr][pc] = FLOOR
                self.status = "Got the key! Find the CHEST!"
            elif cell == TRAP:
                self.player.rect.topleft = self.start_pos
                self.status = "You fell into a trap! Back to start."
            elif cell == KEY:
                self.player.has_key = True
                self.grid[pr][pc] = FLOOR
                self.status = "Got the key! Find the CHEST!"
            elif cell == CHEST and self.player.has_key:
                self.won = True
                self.status = "Treasure found!"


    def draw_minimap(self):
        map_width = COLS * MINIMAP_TILE
        map_height = ROWS * MINIMAP_TILE

        x0 = WIDTH - map_width - MINIMAP_MARGIN
        y0 = MINIMAP_MARGIN

        # Background and border
        pygame.draw.rect(
            self.screen,
            (10, 10, 15),
            (x0 - 3, y0 - 3, map_width + 6, map_height + 6)
        )

        # Draw dungeon cells
        for r in range(ROWS):
            for c in range(COLS):
                cell = self.grid[r][c]

                if cell == WALL:
                    color = (45, 40, 55)
                else:
                    color = (190, 180, 160)

                rect = pygame.Rect(
                    x0 + c * MINIMAP_TILE,
                    y0 + r * MINIMAP_TILE,
                    MINIMAP_TILE,
                    MINIMAP_TILE
                )

                pygame.draw.rect(self.screen, color, rect)

        # Draw the key
        for r in range(ROWS):
            for c in range(COLS):
                if self.grid[r][c] == KEY:
                    pygame.draw.rect(
                        self.screen,
                        (255, 230, 60),
                        (
                            x0 + c * MINIMAP_TILE,
                            y0 + r * MINIMAP_TILE,
                            MINIMAP_TILE,
                            MINIMAP_TILE
                        )
                    )

        # Draw the chest
        for r in range(ROWS):
            for c in range(COLS):
                if self.grid[r][c] == CHEST:
                    pygame.draw.rect(
                        self.screen,
                        (180, 120, 20),
                        (
                            x0 + c * MINIMAP_TILE,
                            y0 + r * MINIMAP_TILE,
                            MINIMAP_TILE,
                            MINIMAP_TILE
                        )
                    )

        # Draw traps
        for r in range(ROWS):
            for c in range(COLS):
                if self.grid[r][c] == TRAP:
                    pygame.draw.rect(
                        self.screen,
                        (180, 50, 50),
                        (
                            x0 + c * MINIMAP_TILE,
                            y0 + r * MINIMAP_TILE,
                            MINIMAP_TILE,
                            MINIMAP_TILE
                        )
                    )

        # Draw player position
        player_col = self.player.rect.centerx // TILE
        player_row = self.player.rect.centery // TILE

        if 0 <= player_row < ROWS and 0 <= player_col < COLS:
            pygame.draw.rect(
                self.screen,
                (50, 120, 255),
                (
                    x0 + player_col * MINIMAP_TILE,
                    y0 + player_row * MINIMAP_TILE,
                    MINIMAP_TILE,
                    MINIMAP_TILE
                )
            )

    def draw_inventory(self):
        inventory_x = WIDTH - 150
        inventory_y = ROWS * TILE + 7

        # Inventory label
        label = self.font.render("INV", True, (200, 200, 200))
        self.screen.blit(label, (inventory_x, inventory_y + 5))

        # Inventory slot
        slot_x = inventory_x + 45
        slot_y = inventory_y
        slot_size = 36

        pygame.draw.rect(
            self.screen,
            (60, 60, 75),
            (slot_x, slot_y, slot_size, slot_size),
            border_radius=4
        )

        pygame.draw.rect(
            self.screen,
            (150, 150, 160),
            (slot_x, slot_y, slot_size, slot_size),
            2,
            border_radius=4
        )

        # Draw key only after it has been collected
        if self.player.has_key:
            center_x = slot_x + slot_size // 2
            center_y = slot_y + slot_size // 2

            # Key ring
            pygame.draw.circle(
                self.screen,
                (255, 230, 60),
                (center_x - 6, center_y - 4),
                6,
                2
            )

            # Key shaft
            pygame.draw.line(
                self.screen,
                (255, 230, 60),
                (center_x, center_y - 4),
                (center_x + 11, center_y - 4),
                3
            )

            # Key teeth
            pygame.draw.line(
                self.screen,
                (255, 230, 60),
                (center_x + 6, center_y - 4),
                (center_x + 6, center_y + 2),
                3
            )

            pygame.draw.line(
                self.screen,
                (255, 230, 60),
                (center_x + 11, center_y - 4),
                (center_x + 11, center_y + 2),
                3
            )

    def draw(self):
        self.screen.fill((30,25,40))
        for r in range(ROWS):
            for c in range(COLS):
                cell = self.grid[r][c]
                rect = pygame.Rect(c*TILE, r*TILE, TILE, TILE)
                pygame.draw.rect(self.screen, COLORS[cell], rect)
                if cell == KEY:
                    pygame.draw.circle(self.screen, (255,240,60),(c*TILE+TILE//2, r*TILE+TILE//2),10)
                elif cell == CHEST:
                    pygame.draw.rect(self.screen,(180,120,20),rect.inflate(-12,-12),border_radius=4)
                elif cell == TRAP:
                    pygame.draw.line(
                        self.screen,
                        (80,20,20),
                        (c*TILE+8, r*TILE+8),
                        (c*TILE+TILE-8, r*TILE+TILE-8),
                        4
                    )
                    pygame.draw.line(
                        self.screen,
                        (80,20,20),
                        (c*TILE+TILE-8, r*TILE+8),
                        (c*TILE+8, r*TILE+TILE-8),
                        4
                    )
        self.player.draw(self.screen)
        if self.guard:
            self.guard.draw(self.screen)
        self.draw_minimap()
        hud = pygame.Rect(0,ROWS*TILE,WIDTH,50)
        pygame.draw.rect(self.screen,(20,20,35),hud)
        st = self.font.render(self.status+"  |  R=Restart", True, (200,200,200))
        self.screen.blit(st,(8,ROWS*TILE+13))
        self.draw_inventory()
        if self.won:
            ov=pygame.Surface((WIDTH,ROWS*TILE),pygame.SRCALPHA)
            ov.fill((0,0,0,140))
            self.screen.blit(ov,(0,0))
            msg=self.big_font.render("TREASURE FOUND!", True,(220,180,30))
            sub=self.font.render("Press R to Play Again",True,(180,180,180))
            self.screen.blit(msg,(WIDTH//2-msg.get_width()//2,ROWS*TILE//2-30))
            self.screen.blit(sub,(WIDTH//2-sub.get_width()//2,ROWS*TILE//2+20))
        pygame.display.flip()

    def run(self):
        running=True
        while running:
            running=self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()

if __name__ == "__main__":
    engine = GameEngine()
    engine.run()
