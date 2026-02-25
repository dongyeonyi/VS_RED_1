import os
import random
import pygame

# ======================
# 초기화
# ======================
pygame.init()
pygame.mixer.init()

W, H = 800, 600
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("은빛산 - 심향 vs 레드")
clock = pygame.time.Clock()
FPS = 60

BASE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

def asset_path(name: str) -> str:
    return os.path.join(ASSETS_DIR, name)

def load_img(name: str, size=None):
    img = pygame.image.load(asset_path(name)).convert_alpha()
    if size:
        img = pygame.transform.smoothscale(img, size)
    return img

# 폰트
kfont_path = os.path.join(ASSETS_DIR, "NanumGothic.ttf")
title_font = pygame.font.Font(kfont_path, 86)
big_font   = pygame.font.Font(kfont_path, 44)
font       = pygame.font.Font(kfont_path, 28)

# ======================
# 사운드 로드
# ======================
def play_bgm(filename, volume=0.5):
    path = asset_path(filename)
    if os.path.exists(path):
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play(-1)

damage_sound = None
damage_path = asset_path("damage.mp3")
if os.path.exists(damage_path):
    try:
        damage_sound = pygame.mixer.Sound(damage_path)
        damage_sound.set_volume(0.8)
    except pygame.error:
        damage_sound = None

# ======================
# UI (버튼/팝업)
# ======================
class Button:
    def __init__(self, rect, text):
        self.rect = pygame.Rect(rect)
        self.text = text

    def draw(self, surf, is_hover=False):
        # 색: 기본/호버
        bg = (40, 40, 55) if not is_hover else (60, 60, 85)
        border = (150, 150, 180)
        pygame.draw.rect(surf, bg, self.rect, border_radius=14)
        pygame.draw.rect(surf, border, self.rect, width=2, border_radius=14)

        txt = font.render(self.text, True, (235, 235, 235))
        txt_rect = txt.get_rect(center=self.rect.center)
        surf.blit(txt, txt_rect)

    def is_clicked(self, mouse_pos, mouse_down):
        return mouse_down and self.rect.collidepoint(mouse_pos)

def draw_dim_popup(surf, title, lines):
    # 반투명 배경
    overlay = pygame.Surface((W, H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    surf.blit(overlay, (0, 0))

    # 팝업 박스
    box = pygame.Rect(120, 130, 560, 340)
    pygame.draw.rect(surf, (25, 25, 35), box, border_radius=16)
    pygame.draw.rect(surf, (170, 170, 200), box, width=2, border_radius=16)

    # 타이틀
    t = big_font.render(title, True, (240, 240, 240))
    surf.blit(t, (box.x + 24, box.y + 18))

    # 본문
    y = box.y + 80
    for line in lines:
        text_surf = font.render(line, True, (230, 230, 230))
        surf.blit(text_surf, (box.x + 24, y))
        y += 34

    # 닫기 안내
    hint = font.render("ESC 또는 아무 곳 클릭: 닫기", True, (200, 200, 200))
    surf.blit(hint, (box.x + 24, box.y + box.height - 40))

# ======================
# 전투 배경 (도트 느낌 다리)
# ======================
def draw_bridge_background(surface):
    surface.fill((10, 10, 18))

    bridge_w = 520
    bridge_x = (W - bridge_w) // 2
    bridge_y = 120
    bridge_h = H - 120

    pygame.draw.rect(surface, (20, 20, 28), (bridge_x, bridge_y, bridge_w, bridge_h))

    plank_color1 = (55, 50, 45)
    plank_color2 = (65, 60, 54)
    plank_h = 10
    gap = 6
    y = bridge_y + 10
    toggle = False
    while y < bridge_y + bridge_h - 10:
        color = plank_color2 if toggle else plank_color1
        pygame.draw.rect(surface, color, (bridge_x + 10, y, bridge_w - 20, plank_h))
        toggle = not toggle
        y += plank_h + gap

    rail_color = (35, 35, 45)
    pygame.draw.rect(surface, rail_color, (bridge_x, bridge_y, 12, bridge_h))
    pygame.draw.rect(surface, rail_color, (bridge_x + bridge_w - 12, bridge_y, 12, bridge_h))

    post_color = (50, 50, 62)
    for py in range(bridge_y + 20, bridge_y + bridge_h, 32):
        pygame.draw.rect(surface, post_color, (bridge_x, py, 12, 6))
        pygame.draw.rect(surface, post_color, (bridge_x + bridge_w - 12, py, 12, 6))

def hit_circle(ax, ay, ar, bx, by, br):
    dx = ax - bx
    dy = ay - by
    return dx*dx + dy*dy <= (ar + br) * (ar + br)

# ======================
# 전투(게임) 루프 함수
# ======================
def run_battle():
    # 이미지 로드
    player_img = load_img("black.png", size=(64, 64))
    boss_img   = load_img("pika.png",  size=(96, 96))

    # 히트박스: 이미지에 맞춘 원형(“그림이랑 똑같게” 느낌)
    player_hit_r = min(player_img.get_width(), player_img.get_height()) // 2
    boss_r       = min(boss_img.get_width(), boss_img.get_height()) // 2

    # 전투 BGM 시작
    play_bgm("battle_bgm.mp3", volume=0.5)

    # 플레이어
    px, py = 400, 500
    speed, focus_speed = 5, 2
    hp = 100

    invuln = 0
    INVULN_FRAMES = FPS  # 1초

    # 플레이어 자동 공격
    player_bullets = []  # [x, y, vy]
    PLAYER_BULLET_R = 4
    PLAYER_BULLET_SPEED = -12
    PLAYER_DMG = 3
    player_shot_timer = 0
    PLAYER_SHOT_EVERY = 6

    # 보스
    bx, by = 400, 120
    boss_hp = 1000
    BOSS_HP_MAX = 1000

    boss_dir = 1
    boss_speed = 3
    boss_change_timer = 0
    BOSS_CHANGE_EVERY = 45

    # 보스 공격
    boss_bullets = []  # [x, y, vx, vy]
    BOSS_BULLET_R = 8
    BOSS_BULLET_SPEED = 6
    BOSS_DMG = 15
    boss_shot_timer = 0
    BOSS_SHOT_EVERY = 5 * FPS

    # 싸라기눈
    snow = []  # [x, y, vy]
    SNOW_R = 4
    SNOW_DMG = 5
    snow_timer = 0
    SNOW_EVERY = 10

    game_over = False
    win = False

    while True:
        # 이벤트
        mouse_down = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return "title"
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_down = True

        keys = pygame.key.get_pressed()

        # 업데이트
        if not game_over and not win:
            if invuln > 0:
                invuln -= 1

            # 이동
            now_speed = focus_speed if (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) else speed
            if keys[pygame.K_LEFT] or keys[pygame.K_a]: px -= now_speed
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]: px += now_speed
            if keys[pygame.K_UP] or keys[pygame.K_w]: py -= now_speed
            if keys[pygame.K_DOWN] or keys[pygame.K_s]: py += now_speed

            px = max(player_hit_r, min(W - player_hit_r, px))
            py = max(player_hit_r, min(H - player_hit_r, py))

            # 보스 이동
            boss_change_timer += 1
            if boss_change_timer % BOSS_CHANGE_EVERY == 0:
                boss_dir = random.choice([-1, 1])
                boss_speed = random.randint(2, 5)

            bx += boss_dir * boss_speed
            if bx < boss_r:
                bx = boss_r
                boss_dir = 1
            if bx > W - boss_r:
                bx = W - boss_r
                boss_dir = -1

            # 싸라기눈
            snow_timer += 1
            if snow_timer % SNOW_EVERY == 0:
                sx = random.randint(0, W)
                sy = -10
                vy = random.randint(3, 6)
                snow.append([sx, sy, vy])

            for s in snow:
                s[1] += s[2]
            snow = [s for s in snow if s[1] < H + 20]

            # 플레이어 자동 발사
            player_shot_timer += 1
            if player_shot_timer % PLAYER_SHOT_EVERY == 0:
                player_bullets.append([px, py, PLAYER_BULLET_SPEED])

            for pb in player_bullets:
                pb[1] += pb[2]
            player_bullets = [pb for pb in player_bullets if pb[1] > -20]

            # 보스 공격(5초 조준탄)
            boss_shot_timer += 1
            if boss_shot_timer >= BOSS_SHOT_EVERY:
                boss_shot_timer = 0
                dx = px - bx
                dy = py - by
                length = (dx*dx + dy*dy) ** 0.5
                if length == 0:
                    length = 1
                vx = (dx / length) * BOSS_BULLET_SPEED
                vy = (dy / length) * BOSS_BULLET_SPEED
                boss_bullets.append([bx, by, vx, vy])

            for bb in boss_bullets:
                bb[0] += bb[2]
                bb[1] += bb[3]
            boss_bullets = [bb for bb in boss_bullets if -50 < bb[0] < W + 50 and -50 < bb[1] < H + 50]

            # 충돌
            took_damage = False

            new_snow = []
            for s in snow:
                if hit_circle(px, py, player_hit_r, s[0], s[1], SNOW_R) and invuln == 0:
                    hp -= SNOW_DMG
                    invuln = INVULN_FRAMES
                    took_damage = True
                else:
                    new_snow.append(s)
            snow = new_snow

            new_boss_bullets = []
            for bb in boss_bullets:
                if hit_circle(px, py, player_hit_r, bb[0], bb[1], BOSS_BULLET_R) and invuln == 0:
                    hp -= BOSS_DMG
                    invuln = INVULN_FRAMES
                    took_damage = True
                else:
                    new_boss_bullets.append(bb)
            boss_bullets = new_boss_bullets

            if took_damage and damage_sound is not None:
                damage_sound.play()

            new_player_bullets = []
            for pb in player_bullets:
                if hit_circle(pb[0], pb[1], PLAYER_BULLET_R, bx, by, boss_r):
                    boss_hp -= PLAYER_DMG
                else:
                    new_player_bullets.append(pb)
            player_bullets = new_player_bullets

            if boss_hp <= 0:
                boss_hp = 0
                win = True

            if hp <= 0:
                hp = 0
                game_over = True

        # 그리기
        draw_bridge_background(screen)

        for s in snow:
            pygame.draw.circle(screen, (200, 220, 255), (int(s[0]), int(s[1])), SNOW_R)

        # 보스 HP바
        bar_w, bar_h = 600, 16
        bar_x = (W - bar_w) // 2
        bar_y = 20
        pygame.draw.rect(screen, (60, 60, 60), (bar_x, bar_y, bar_w, bar_h))
        ratio = boss_hp / BOSS_HP_MAX
        pygame.draw.rect(screen, (220, 50, 50), (bar_x, bar_y, int(bar_w * ratio), bar_h))

        # 보스 이미지
        screen.blit(boss_img, boss_img.get_rect(center=(int(bx), int(by))))

        # 보스탄
        for bb in boss_bullets:
            pygame.draw.circle(screen, (255, 120, 120), (int(bb[0]), int(bb[1])), BOSS_BULLET_R)

        # 플레이어탄
        for pb in player_bullets:
            pygame.draw.circle(screen, (255, 160, 40), (int(pb[0]), int(pb[1])), PLAYER_BULLET_R)

        # 플레이어(무적 깜빡임)
        blink_off = (invuln > 0) and ((invuln // 5) % 2 == 0)
        if not blink_off:
            screen.blit(player_img, player_img.get_rect(center=(int(px), int(py))))

        # UI
        screen.blit(font.render(f"HP: {hp}", True, (230, 230, 230)), (12, 12))

        if game_over:
            screen.blit(font.render("GAME OVER", True, (255, 80, 80)), (W // 2 - 80, H // 2))
        if win:
            screen.blit(font.render("YOU WIN!", True, (120, 255, 120)), (W // 2 - 60, H // 2))

        pygame.display.flip()
        clock.tick(FPS)

# ======================
# 타이틀 화면
# ======================
def run_title():
    # 타이틀 BGM 시작
    play_bgm("start.mp3", volume=0.55)

    btn_play = Button((W//2 - 140, 330, 280, 56), "게임 플레이")
    btn_help = Button((W//2 - 140, 400, 280, 56), "게임 방법")

    show_help = False
    help_lines = [
        "은빛산 정상에 도달한 것을 환영합니다.",
        "레드를 이기고, 최강의 트레이너임을 증명하세요.",
        "",
        "기본 이동 - wasd or 방향키",
        "섬세 이동 - shift를 누른 채 이동",
    ]

    while True:
        mouse_down = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_down = True
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if show_help:
                    show_help = False

        mouse_pos = pygame.mouse.get_pos()

        # 배경(타이틀용: 어두운 그라데이션 느낌)
        screen.fill((10, 10, 18))
        pygame.draw.circle(screen, (25, 25, 40), (120, 90), 140)
        pygame.draw.circle(screen, (18, 18, 30), (680, 520), 200)

        # 타이틀 텍스트
        title = title_font.render("VS  RED", True, (245, 245, 245))
        subtitle = font.render("은빛산 최종 결전", True, (200, 200, 200))
        screen.blit(title, title.get_rect(center=(W//2, 170)))
        screen.blit(subtitle, subtitle.get_rect(center=(W//2, 220)))

        # 버튼
        hover_play = btn_play.rect.collidepoint(mouse_pos)
        hover_help = btn_help.rect.collidepoint(mouse_pos)
        btn_play.draw(screen, is_hover=hover_play)
        btn_help.draw(screen, is_hover=hover_help)

        if not show_help:
            if btn_play.is_clicked(mouse_pos, mouse_down):
                return "battle"
            if btn_help.is_clicked(mouse_pos, mouse_down):
                show_help = True
        else:
            # 도움말 팝업 표시
            draw_dim_popup(screen, "게임 방법", help_lines)
            # 팝업 떠 있을 때 클릭하면 닫기
            if mouse_down:
                show_help = False

        pygame.display.flip()
        clock.tick(FPS)

# ======================
# 메인 상태 머신
# ======================
state = "title"
while True:
    if state == "title":
        result = run_title()
        if result == "quit":
            break
        if result == "battle":
            state = "battle"

    elif state == "battle":
        result = run_battle()
        if result == "quit":
            break
        if result == "title":
            state = "title"

pygame.quit()