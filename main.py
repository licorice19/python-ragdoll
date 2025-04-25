import pygame
import pymunk
import pymunk.pygame_util
import math
import sys
import random

# --- Константы ---
WIDTH, HEIGHT = 800, 600
FPS = 60
WHITE = (255, 255, 255); RED = (255, 0, 0); GREEN = (0, 255, 0); BLUE = (0, 0, 255); BLACK = (0, 0, 0); GREY = (128,128,128); YELLOW=(255,255,0)

# --- Категории и Маски для Столкновений ---
CAT_FRONT_LIMB = 0b1    # 1
CAT_BACK_LIMB  = 0b10   # 2
CAT_TORSO_HEAD = 0b100  # 4
CAT_PLATFORM   = 0b1000 # 8
# ALL_MASK       = pymunk.ShapeFilter.ALL_MASKS_DEFAULT # Убрали эту строку

# Маски для взаимодействия
MASK_FRONT_LIMB = CAT_BACK_LIMB | CAT_TORSO_HEAD | CAT_PLATFORM
MASK_BACK_LIMB  = CAT_FRONT_LIMB | CAT_TORSO_HEAD | CAT_PLATFORM
MASK_TORSO_HEAD = CAT_FRONT_LIMB | CAT_BACK_LIMB | CAT_PLATFORM
MASK_PLATFORM   = CAT_FRONT_LIMB | CAT_BACK_LIMB | CAT_TORSO_HEAD

# Маска для выбора мышкой (все части рэгдолла)
MASK_MOUSE_PICK = CAT_FRONT_LIMB | CAT_BACK_LIMB | CAT_TORSO_HEAD

# --- Настройка Pygame и Pymunk ---
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pymunk: Профильный Рэгдолл (2 Руки, 2 Ноги)")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 28)

space = pymunk.Space()
space.gravity = (0, -900)
space.iterations = 35
draw_options = pymunk.pygame_util.DrawOptions(screen)
pymunk.pygame_util.positive_y_is_up = True

# --- Создание Платформы ---
platform_body = pymunk.Body(body_type=pymunk.Body.STATIC)
platform_shape = pymunk.Segment(platform_body, (50, 50), (WIDTH - 50, 50), 5)
platform_shape.friction = 1.0
platform_shape.elasticity = 0.7
platform_shape.filter = pymunk.ShapeFilter(categories=CAT_PLATFORM, mask=MASK_PLATFORM) # Назначаем категорию и маску
space.add(platform_body, platform_shape)

# --- Функция создания Рэгдолла ---
def create_ragdoll(space, position, ragdoll_group_id):
    """Создает рэгдолла в профиль в заданной позиции"""
    x_base, y_base = position
    bodies = {}
    shapes = {}
    joints = {}

    # Параметры рэгдолла (как раньше)
    torso_h, torso_w = 90, 15; upper_arm_len, lower_arm_len = 40, 35; arm_w = 8
    thigh_len, shin_len = 45, 40; leg_w = 10; head_r = 15; neck_len = 10; neck_w = 6
    m_torso = 5.0; m_head = 1.5; m_neck = 0.4; m_upper_arm = 0.8; m_lower_arm = 0.6; m_thigh = 1.2; m_shin = 1.0
    limb_friction = 0.7; limb_elasticity = 0.1; torso_friction = 0.7; torso_elasticity = 0.1; head_friction = 0.7; head_elasticity = 0.1

    # --- Торс, Шея, Голова (Категория CAT_TORSO_HEAD) ---
    torso_filter = pymunk.ShapeFilter(group=ragdoll_group_id, categories=CAT_TORSO_HEAD, mask=MASK_TORSO_HEAD)
    # Торс
    moment = pymunk.moment_for_box(m_torso, (torso_w, torso_h)); bodies["torso"] = pymunk.Body(m_torso, moment)
    bodies["torso"].position = x_base, y_base; shapes["torso"] = pymunk.Poly.create_box(bodies["torso"], (torso_w, torso_h), radius=1)
    shapes["torso"].friction = torso_friction; shapes["torso"].elasticity = torso_elasticity; shapes["torso"].filter = torso_filter
    space.add(bodies["torso"], shapes["torso"])
    # Шея
    neck_anchor_torso_y = torso_h / 2; neck_center_y = y_base + neck_anchor_torso_y + neck_len / 2
    moment = pymunk.moment_for_segment(m_neck, (0,-neck_len/2), (0,neck_len/2), neck_w/2); bodies["neck"] = pymunk.Body(m_neck, moment)
    bodies["neck"].position = x_base, neck_center_y; shapes["neck"] = pymunk.Segment(bodies["neck"], (0,-neck_len/2), (0,neck_len/2), neck_w/2)
    shapes["neck"].friction = head_friction; shapes["neck"].elasticity = head_elasticity; shapes["neck"].filter = torso_filter # Та же категория/маска что и торс/голова
    space.add(bodies["neck"], shapes["neck"])
    # Голова
    head_anchor_neck_y = neck_len / 2; head_center_y = neck_center_y + head_anchor_neck_y + head_r * 0.8
    moment = pymunk.moment_for_circle(m_head, 0, head_r); bodies["head"] = pymunk.Body(m_head, moment)
    bodies["head"].position = x_base, head_center_y; shapes["head"] = pymunk.Circle(bodies["head"], head_r)
    shapes["head"].friction = head_friction; shapes["head"].elasticity = head_elasticity; shapes["head"].filter = torso_filter
    space.add(bodies["head"], shapes["head"])
    # Соединения
    joints["torso_neck"] = pymunk.PivotJoint(bodies["torso"], bodies["neck"], (0, neck_anchor_torso_y), (0, -neck_len/2))
    joints["limit_torso_neck"] = pymunk.RotaryLimitJoint(bodies["torso"], bodies["neck"], -math.pi/8, math.pi/8)
    joints["neck_head"] = pymunk.PivotJoint(bodies["neck"], bodies["head"], (0, head_anchor_neck_y), (0, -head_r*0.5))
    joints["limit_neck_head"] = pymunk.RotaryLimitJoint(bodies["neck"], bodies["head"], -math.pi/6, math.pi/6)
    space.add(joints["torso_neck"], joints["limit_torso_neck"], joints["neck_head"], joints["limit_neck_head"])

    # --- Конечности (Руки и Ноги) ---
    # Параметры для каждой конечности: префикс, смещение X, категория, маска
    limb_definitions = [
        # Руки
        ("r_arm", torso_w / 2, CAT_FRONT_LIMB, MASK_FRONT_LIMB), # Правая рука (передний план)
        ("l_arm", -torso_w / 2, CAT_BACK_LIMB, MASK_BACK_LIMB),  # Левая рука (задний план)
        # Ноги
        ("r_leg", torso_w / 4, CAT_FRONT_LIMB, MASK_FRONT_LIMB), # Правая нога (передний план)
        ("l_leg", -torso_w / 4, CAT_BACK_LIMB, MASK_BACK_LIMB)  # Левая нога (задний план)
    ]

    for prefix, x_center_offset, category, mask in limb_definitions:
        is_arm = "arm" in prefix
        is_leg = "leg" in prefix

        # Определяем точки крепления и длины сегментов
        if is_arm:
            attach_y_torso = torso_h * 0.4
            len1, len2 = upper_arm_len, lower_arm_len
            w = arm_w
            m1, m2 = m_upper_arm, m_lower_arm
            joint_prefix = "shoulder" if is_arm else "hip"
            limit1_min, limit1_max = -math.pi * 0.7, math.pi * 0.7 # Плечо/Бедро
            limit2_min, limit2_max = -0.1, math.pi * 0.7 # Локоть/Колено (руки)
        elif is_leg:
            attach_y_torso = -torso_h * 0.45
            len1, len2 = thigh_len, shin_len
            w = leg_w
            m1, m2 = m_thigh, m_shin
            joint_prefix = "hip"
            limit1_min, limit1_max = -math.pi * 0.6, math.pi * 0.4 # Плечо/Бедро
            limit2_min, limit2_max = -math.pi*0.8, 0.1 # Локоть/Колено (ноги)
        else: continue # Пропускаем, если не рука и не нога

        # Фильтр для этой конечности
        limb_filter = pymunk.ShapeFilter(group=ragdoll_group_id, categories=category, mask=mask)

        # --- Верхний сегмент ---
        center1_y = y_base + attach_y_torso - len1 / 2
        moment1 = pymunk.moment_for_box(m1, (w, len1))
        bodies[prefix+"1"] = pymunk.Body(m1, moment1)
        bodies[prefix+"1"].position = x_base + x_center_offset, center1_y
        shapes[prefix+"1"] = pymunk.Poly.create_box(bodies[prefix+"1"], (w, len1), radius=1)
        shapes[prefix+"1"].friction = limb_friction; shapes[prefix+"1"].elasticity = limb_elasticity; shapes[prefix+"1"].filter = limb_filter
        space.add(bodies[prefix+"1"], shapes[prefix+"1"])

        # Сустав 1 (Плечо/Бедро)
        joints[prefix+"_"+joint_prefix] = pymunk.PivotJoint(bodies["torso"], bodies[prefix+"1"], (0, attach_y_torso), (0, len1 / 2))
        joints["limit_"+prefix+"_"+joint_prefix] = pymunk.RotaryLimitJoint(bodies["torso"], bodies[prefix+"1"], limit1_min, limit1_max)
        space.add(joints[prefix+"_"+joint_prefix], joints["limit_"+prefix+"_"+joint_prefix])

        # --- Нижний сегмент ---
        attach_y_upper = -len1 / 2 # Точка крепления на верхнем сегменте (локоть/колено)
        center2_y = center1_y + attach_y_upper - len2 / 2
        moment2 = pymunk.moment_for_box(m2, (w, len2))
        bodies[prefix+"2"] = pymunk.Body(m2, moment2)
        bodies[prefix+"2"].position = x_base + x_center_offset, center2_y
        shapes[prefix+"2"] = pymunk.Poly.create_box(bodies[prefix+"2"], (w, len2), radius=1)
        shapes[prefix+"2"].friction = limb_friction; shapes[prefix+"2"].elasticity = limb_elasticity; shapes[prefix+"2"].filter = limb_filter
        space.add(bodies[prefix+"2"], shapes[prefix+"2"])

        # Сустав 2 (Локоть/Колено)
        joint_prefix2 = "elbow" if is_arm else "knee"
        joints[prefix+"_"+joint_prefix2] = pymunk.PivotJoint(bodies[prefix+"1"], bodies[prefix+"2"], (0, attach_y_upper), (0, len2 / 2))
        joints["limit_"+prefix+"_"+joint_prefix2] = pymunk.RotaryLimitJoint(bodies[prefix+"1"], bodies[prefix+"2"], limit2_min, limit2_max)
        space.add(joints[prefix+"_"+joint_prefix2], joints["limit_"+prefix+"_"+joint_prefix2])

    return bodies, shapes, joints

# --- Создаем Рэгдолла ---
ragdoll_group_id = 1 # Все части ОДНОГО рэгдолла в этой группе
ragdoll_parts = create_ragdoll(space, (WIDTH / 2, HEIGHT - 150), ragdoll_group_id)

# --- Переменные для Drag & Drop ---
selected_shape = None; selected_body = None; mouse_joint = None
mouse_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)

# --- Основной цикл ---
running = True
while running:
    dt = 1.0 / FPS
    mouse_pos_pymunk = None

    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: running = False
            elif event.key == pygame.K_SPACE: # Сброс
                 if ragdoll_parts:
                     for body in ragdoll_parts[0].values(): space.remove(body)
                     for shape in ragdoll_parts[1].values(): space.remove(shape)
                     for joint in ragdoll_parts[2].values(): space.remove(joint)
                 ragdoll_parts = create_ragdoll(space, (random.randint(150, WIDTH-150), HEIGHT - 150), ragdoll_group_id)
                 if mouse_joint: space.remove(mouse_joint); mouse_joint = None; selected_body = None; selected_shape = None

        # Drag & Drop
        mouse_pos_pygame = pygame.mouse.get_pos()
        mouse_pos_pymunk = pymunk.pygame_util.get_mouse_pos(screen)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Ищем ближайшую форму из нужных категорий
            point_query = space.point_query_nearest(mouse_pos_pymunk, 10, pymunk.ShapeFilter(mask=MASK_MOUSE_PICK))
            if point_query and point_query.shape and point_query.shape.body.body_type == pymunk.Body.DYNAMIC:
                selected_shape = point_query.shape; selected_body = selected_shape.body
                selected_body.activate()
                anchor_b = selected_body.world_to_local(mouse_pos_pymunk)
                anchor_a = (0,0); rest_length = 0; stiffness = 5000; damping = 150
                mouse_body.position = mouse_pos_pymunk
                mouse_joint = pymunk.DampedSpring(mouse_body, selected_body, anchor_a, anchor_b, rest_length, stiffness, damping)
                space.add(mouse_joint)

        elif event.type == pygame.MOUSEMOTION:
            if mouse_joint:
                mouse_body.position = mouse_pos_pymunk
                if selected_body: selected_body.activate()

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if mouse_joint:
                space.remove(mouse_joint)
                mouse_joint = None; selected_body = None; selected_shape = None

    # Шаг симуляции Pymunk
    space.step(dt)

    # Отрисовка
    screen.fill(BLACK)
    space.debug_draw(draw_options)
    # Вспомогательная отрисовка drag&drop
    if mouse_joint and selected_body:
         point_on_body_world = selected_body.local_to_world(mouse_joint.anchor_b)
         pygame.draw.circle(screen, YELLOW, pymunk.pygame_util.to_pygame(point_on_body_world, screen), 5)
         pygame.draw.line(screen, YELLOW, pymunk.pygame_util.to_pygame(point_on_body_world, screen), pymunk.pygame_util.to_pygame(mouse_body.position, screen), 1)

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()