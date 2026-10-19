import os
import sys
import time
import base64
import argparse
from collections import deque
import numpy as np
from PIL import Image

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BUTTON_UI_DIR = os.path.join(BASE_DIR, 'Button UI')
BUTTONS_DIR = os.path.join(BASE_DIR, 'buttons')
WWW_BUTTONS_DIR = os.path.join(BASE_DIR, 'www', 'buttons')
ANDROID_BUTTONS_DIR = os.path.join(BASE_DIR, 'android', 'app', 'src', 'main', 'assets', 'public', 'buttons')

UI_JS_PATHS = [
    os.path.join(BASE_DIR, 'js', 'ui.js'),
    os.path.join(BASE_DIR, 'www', 'js', 'ui.js'),
    os.path.join(BASE_DIR, 'android', 'app', 'src', 'main', 'assets', 'public', 'js', 'ui.js')
]

ITEM_PROMPTS = {
    # 1. Items & Tools
    'sword_wood': {
        'name': 'Pedang kayu.png',
        'prompt': (
            'clean 3d voxel art icon of a wooden broadsword with thick blocky wooden blade, crossguard and brown wrapped grip handle, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant clean colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'hoe': {
        'name': 'Cangkul.png',
        'prompt': (
            'clean 3d voxel art icon of a farming hoe with curved wooden handle and sturdy steel hoe blade angled downward, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant clean colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'sugar_cane': {
        'name': 'Tebu.png',
        'prompt': (
            'clean 3d voxel art icon of fresh green sugar cane bamboo stalks with segmented joints and fresh green leafy shoots, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant clean green colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not minecraft sprite'
        )
    },
    'sugar': {
        'name': 'Gula.png',
        'prompt': (
            'clean 3d voxel art icon of a rustic wooden bowl filled with pure white sugar cubes and sparkling crystalline sugar, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant clean colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not minecraft sprite'
        )
    },
    'cake': {
        'name': 'Kue.png',
        'prompt': (
            'clean 3d voxel art icon of a delicious round frosted celebration cake with creamy white icing, chocolate sponge layers, and red berries on top, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant clean colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not minecraft sprite'
        )
    },
    'rope': {
        'name': 'Tali.png',
        'prompt': (
            'clean 3d voxel art icon of a neatly coiled brown hemp rope bundle with lasso loop, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant clean colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not minecraft sprite'
        )
    },
    'saddle': {
        'name': 'Sadel.png',
        'prompt': (
            'clean 3d voxel art icon of a leather horse riding saddle with silver stirrups, buckles, and girth straps, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant warm leather colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not minecraft sprite'
        )
    },
    'pet_charm': {
        'name': 'Jimat pawang.png',
        'prompt': (
            'clean 3d voxel art icon of a mystical beast tamer talisman amulet pendant with glowing turquoise jewel and golden bezel frame, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant clean colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not minecraft sprite'
        )
    },
    'log_pass': {
        'name': 'Log pass.png',
        'prompt': (
            'clean 3d voxel art icon of a vintage brass pocket compass navigation dial with glass cover and directional compass needle, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant metallic colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not minecraft sprite'
        )
    },
    'dungeon_changer': {
        'name': 'Dungeon changer.png',
        'prompt': (
            'clean 3d voxel art icon of an ancient legendary dungeon key artifact with glowing purple mystic gem and ornate golden handle teeth, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, glowing magical runes, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not minecraft sprite'
        )
    },

    # 2. UI Action Buttons
    'build': {
        'name': 'Build.png',
        'prompt': (
            'clean 3d voxel art icon of stacked red brick construction blocks with a mason trowel tool, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant clean colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not minecraft sprite'
        )
    },
    'bag': {
        'name': 'Bag.png',
        'prompt': (
            'clean 3d voxel art icon of an adventurer leather backpack knapsack with brass buckles, side pouches, and bedroll, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant clean colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not minecraft sprite'
        )
    },
    'skills': {
        'name': 'Skills.png',
        'prompt': (
            'clean 3d voxel art icon of a brilliant shining golden five-point star talisman radiating energy sparks, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant glowing golden colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not minecraft sprite'
        )
    },
    'craft': {
        'name': 'Craft.png',
        'prompt': (
            'clean 3d voxel art icon of a blacksmith hammer crossed with a steel wrench tool, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant metallic colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not minecraft sprite'
        )
    },

    # 3. Furniture & Workstations
    'f_table': {
        'name': 'Meja kayu.png',
        'prompt': (
            'clean 3d voxel art icon of a rustic wooden dining table with four sturdy legs and smooth oak plank tabletop, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, warm wooden textures, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not minecraft sprite'
        )
    },
    'f_chair': {
        'name': 'Kursi kayu.png',
        'prompt': (
            'clean 3d voxel art icon of a comfortable wooden armchair with backrest and arm rests, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, warm wood colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not minecraft sprite'
        )
    },
    'f_bed': {
        'name': 'Tempat tidur.png',
        'prompt': (
            'clean 3d voxel art icon of a cozy wooden bed frame with fluffy white mattress, red blanket quilt, and soft pillow, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant clean colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not minecraft sprite'
        )
    },
    'f_chest': {
        'name': 'Peti penyimpanan.png',
        'prompt': (
            'clean 3d voxel art icon of a wooden storage treasure chest with iron bands, hinges, and front keyhole latch, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, warm wood and iron colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not minecraft sprite'
        )
    },
    'f_boat': {
        'name': 'Perahu kayu.png',
        'prompt': (
            'clean 3d voxel art icon of a wooden rowboat canoe with wooden hull interior and two wooden rowing paddles oars resting across, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant oak wood colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not minecraft sprite'
        )
    },
    'f_board': {
        'name': 'Papan quest.png',
        'prompt': (
            'clean 3d voxel art icon of a wooden bulletin quest board sign on two posts with pinned parchment paper notices and red seal, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, warm wood colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not minecraft sprite'
        )
    },
    'f_workbench': {
        'name': 'Meja kerja.png',
        'prompt': (
            'clean 3d voxel art icon of a carpenter woodworking workbench with side metal vise clamp, drawer, and wooden tabletop, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, rich wood colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not minecraft sprite'
        )
    },
    'f_anvil': {
        'name': 'Landasan tempa.png',
        'prompt': (
            'clean 3d voxel art icon of a heavy dark cast iron blacksmith anvil mounted on a sturdy solid wood log stump, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, steel and timber colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not minecraft sprite'
        )
    },
    'f_stove': {
        'name': 'Tungku masak.png',
        'prompt': (
            'clean 3d voxel art icon of a cobblestone cooking stove oven with glowing red fire embers inside and a cooking pot kettle on top, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, stone and fire glow colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not minecraft sprite'
        )
    },
    'f_campfire': {
        'name': 'Api unggun.png',
        'prompt': (
            'clean 3d voxel art icon of a cozy wilderness campfire with crossed wooden logs, round stone circle hearth, and vibrant orange yellow flames, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, warm fire glow colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not minecraft sprite'
        )
    },
    'f_house': {
        'name': 'Rumah kayu.png',
        'prompt': (
            'clean 3d voxel art icon of a cute cozy wooden cabin cottage house with pitched timber roof, front wooden door, and glass window, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, charming wooden colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not minecraft sprite'
        )
    },
    'f_castle1': {
        'name': 'Kastil T1.png',
        'prompt': (
            'clean 3d voxel art icon of a medieval stone castle fortress keep tier 1 with stone crenelated battlements, '
            'four corner watchtowers with red timber roofs, and an arched wooden reinforced double gate entrance, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, clean stone grey and warm terracotta roof colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not minecraft sprite'
        )
    },
    'f_castle2': {
        'name': 'Kastil T2.png',
        'prompt': (
            'clean 3d voxel art icon of a grand medieval stone citadel castle tier 2 with tall octagonal stone corner towers topped with pointed royal blue cone spires and golden finials, '
            'crenelated battlements, a raised central keep, and a wrought-iron portcullis double gate, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, rich blue, gold, and grey stone colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not minecraft sprite'
        )
    },
    'f_castle3': {
        'name': 'Kastil T3.png',
        'prompt': (
            'clean 3d voxel art icon of a massive majestic imperial royal palace cathedral fortress tier 3 made of dark obsidian stone with golden crown trims, '
            'towering spires topped with golden finials, a glowing purple arcane crystal atop the central highest spire, and a colossal gilded double gate with burning braziers, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, opulent gold, dark slate, and glowing purple crystal colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not minecraft sprite'
        )
    },
    'f_fence1': {
        'name': 'Pagar kayu T1.png',
        'prompt': (
            'clean 3d voxel art icon of a rustic wooden fence segment tier 1 with two vertical pointed wooden posts and two horizontal timber crossbeams, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, warm natural oak wood colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not minecraft sprite'
        )
    },
    'f_fence2': {
        'name': 'Pagar batu T2.png',
        'prompt': (
            'clean 3d voxel art icon of a sturdy carved stone wall fence segment tier 2 with crenelated battlements, cobblestone texture, and a mounted iron torch brazier with bright flame, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, clean grey stone and fiery orange flame colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not minecraft sprite'
        )
    },
    'f_fence3': {
        'name': 'Benteng imperial T3.png',
        'prompt': (
            'clean 3d voxel art icon of an imposing tall imperial fortress wall segment tier 3 made of dark reinforced stone blocks, '
            'topped with ornate golden battlements and a glowing royal flame brazier bowl, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, dark slate and gleaming golden colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not minecraft sprite'
        )
    },
    'f_gate1': {
        'name': 'Gerbang pagar T1.png',
        'prompt': (
            'clean 3d voxel art icon of a rustic wooden fence gate tier 1 with two sturdy timber side posts, an overhead wooden lintel beam, and double swinging wooden gate doors with black iron hinges, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, rich warm wood and dark iron colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not minecraft sprite'
        )
    },
    'f_gate2': {
        'name': 'Gerbang pagar T2.png',
        'prompt': (
            'clean 3d voxel art icon of a fortified stone archway gate tier 2 with heavy stone pillars, hanging lanterns, and a raised heavy black wrought-iron portcullis grate grill, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, stone grey and dark steel colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not minecraft sprite'
        )
    },
    'f_gate3': {
        'name': 'Gerbang benteng T3.png',
        'prompt': (
            'clean 3d voxel art icon of a grand imperial fortress gatehouse tier 3 with colossal dark stone pillars crowned with gold, '
            'a majestic carved archway, golden lion crest medallion, and heavy double reinforced dark iron gate doors with gold rivets and burning wall braziers, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, opulent gold, dark slate, and flame colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not minecraft sprite'
        )
    },

    # 4. Shields / Tameng (Persis Berdasarkan Model 3D In-Game di NEW MODEL/Tameng.html & js/player/shields.js)
    'shield_wood': {
        'name': 'Tameng kayu.png',
        'prompt': (
            'clean 3d voxel art icon of a rectangular wooden shield made of horizontal brown oak timber planks, '
            'bound with a dark wooden border rim and reinforced with a thick circular cast-iron metal boss plate in the center, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, rich warm wood colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'shield_iron': {
        'name': 'Tameng ksatria besi.png',
        'prompt': (
            'clean 3d voxel art icon of a gallant knight iron heater shield tapering downward to a point with polished silver steel plates, '
            'dark gunmetal steel border rim, and a prominent gleaming golden yellow cross crest embossed in the center with a central iron rivet boss, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant clean metallic colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'shield_flame': {
        'name': 'Tameng bara.png',
        'prompt': (
            'clean 3d voxel art icon of a circular round shield forged from blackened charred volcanic metal plates, '
            'centered with a blazing voxel fire flame crest glowing from bright yellow core to orange and crimson fire embers with subtle spark particles, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant warm fiery glow colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'shield_venom': {
        'name': 'Tameng bisa.png',
        'prompt': (
            'clean 3d voxel art icon of a toxic venom round shield with three dripping neon green acid slime droplets hanging from the bottom rim, '
            'crafted from dark mossy metal plates with a glowing vibrant lime-green poison slime core blob in the center, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant toxic green colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'shield_storm': {
        'name': 'Tameng badai.png',
        'prompt': (
            'clean 3d voxel art icon of an electric storm diamond-shaped rhombus shield made of gleaming golden metal plates with bronze border, '
            'featuring a prominent vertical jagged black obsidian lightning bolt emblem zig-zagging down the center, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant golden and electric colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'shield_frost': {
        'name': 'Tameng fajar beku.png',
        'prompt': (
            'clean 3d voxel art icon of a frost dawn pointed hexagonal shield carved from translucent pale glacial cyan ice crystal, '
            'bordered by deep frozen blue crystal rim, featuring an intricate pure white 8-pointed snowflake star crest in the center, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant icy blue and white colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'shield_dark': {
        'name': 'Tameng bayangan.png',
        'prompt': (
            'clean 3d voxel art icon of a tall gothic shadow tower shield with three sharp crown spikes on the top edge, '
            'crafted from dark purple obsidian stone, featuring a glowing mystical violet eldritch eye with a vertical black slit pupil in the center, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, deep purple and dark obsidian colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'shield_carapace': {
        'name': 'Tameng karapas kelabang.png',
        'prompt': (
            'clean 3d voxel art icon of a heavy chitin carapace shield made from overlapping segmented crimson red centipede shell plates, '
            'reinforced with sharp black chitinous spikes along the outer edge and rugged insect exoskeleton texture, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant crimson red and insect shell colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },

    # 5. UI Buttons
    'chat': {
        'name': 'Tombol chat.png',
        'prompt': (
            'clean 3d voxel art icon of a cute rounded speech chat bubble with three white dots ellipsis in the center, '
            'crafted from vibrant glossy cyan and sky blue volumetric blocks, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant clean colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'gear': {
        'name': 'Tombol pengaturan.png',
        'prompt': (
            'clean 3d voxel art icon of a mechanical cog gear wheel with six sturdy gear teeth and center axle hole, '
            'forged from polished steel and warm brass golden metallic cubic blocks, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant clean metallic colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },

    # 6. Proficiencies / Keahlian
    'prof_logging': {
        'name': 'Keahlian penebangan.png',
        'prompt': (
            'clean 3d voxel art icon of a heavy steel woodsman axe chopping into a thick round oak tree stump log with scattered flying wood chips, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, rich warm timber colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'prof_mining': {
        'name': 'Keahlian penambangan.png',
        'prompt': (
            'clean 3d voxel art icon of a sharp steel miner pickaxe breaking open a rugged gray stone rock revealing sparkling glowing blue mineral crystals, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant stone and crystal colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'prof_harvesting': {
        'name': 'Keahlian pemanenan.png',
        'prompt': (
            'clean 3d voxel art icon of a small curved steel sickle harvesting fresh green herbs, clover leaves, and flowering plants, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant lush green botanical colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'prof_combat': {
        'name': 'Keahlian pertarungan.png',
        'prompt': (
            'clean 3d voxel art icon of two crossed gallant knight steel broadswords with red ruby crossguards radiating combat energy sparks, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant steel and ruby colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'prof_blocking': {
        'name': 'Keahlian penangkisan.png',
        'prompt': (
            'clean 3d voxel art icon of a reinforced knight steel kite shield deflecting an incoming impact with radiant blue kinetic barrier sparks, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant metallic defense colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'prof_crafting': {
        'name': 'Keahlian kriya.png',
        'prompt': (
            'clean 3d voxel art icon of a heavy blacksmith forging hammer crossed over a steel wrench tool above a dark iron anvil, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant metallic iron colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'prof_cooking': {
        'name': 'Keahlian memasak.png',
        'prompt': (
            'clean 3d voxel art icon of a rustic cast iron skillet frying pan with a sizzling golden sunny-side-up egg and fragrant steam puffs, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, appetizing food colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'prof_farming': {
        'name': 'Keahlian pertanian.png',
        'prompt': (
            'clean 3d voxel art icon of a tied golden sheaf bundle of ripe wheat stalks alongside a fresh orange carrot and green cabbage, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, warm golden harvest colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'prof_agility': {
        'name': 'Keahlian kelincahan.png',
        'prompt': (
            'clean 3d voxel art icon of a pair of winged leather boots dashing forward surrounded by breezy swirling wind streaks, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant swift energy colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },

    # 7. Status Effects / Buffs
    'eff_bleed': {
        'name': 'Efek pendarahan.png',
        'prompt': (
            'clean 3d voxel art icon of three glossy crimson red blood droplets falling in a vertical trail, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant crimson blood red colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'eff_shock': {
        'name': 'Efek sengatan listrik.png',
        'prompt': (
            'clean 3d voxel art icon of a crackling jagged electric lightning spark bolt radiating bright cyan and yellow electrical sparks, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant electric cyan yellow colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'eff_venom': {
        'name': 'Efek racun.png',
        'prompt': (
            'clean 3d voxel art icon of a glass alchemical potion bottle flask filled with bubbling neon lime green toxic acid poison liquid emitting toxic vapor, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant toxic green colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'eff_frost': {
        'name': 'Efek fajar beku.png',
        'prompt': (
            'clean 3d voxel art icon of a symmetrical sparkling six-pointed ice snowflake star crystal with glowing pale blue frost particles, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant icy blue white colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'eff_quake': {
        'name': 'Efek gempa.png',
        'prompt': (
            'clean 3d voxel art icon of shattered cracked earth rock ground breaking apart with an explosive fiery orange shockwave, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant earth and fire colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'eff_swift': {
        'name': 'Efek kelincahan angin.png',
        'prompt': (
            'clean 3d voxel art icon of swirling spiraling wind gust gale breeze vortex in soft white and sky blue hues, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, airy wind colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'eff_guard': {
        'name': 'Efek pertahanan perisai.png',
        'prompt': (
            'clean 3d voxel art icon of a radiant glowing golden celestial aegis barrier shield crest emitting a protective energy dome, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant glowing gold colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'eff_greed': {
        'name': 'Efek pemburu harta.png',
        'prompt': (
            'clean 3d voxel art icon of an overflowing burlap coin pouch bag stuffed with sparkling golden coins, emeralds, and rubies, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, rich treasure gold colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'eff_regen': {
        'name': 'Efek regenerasi jiwa.png',
        'prompt': (
            'clean 3d voxel art icon of a faceted crystalline pink ruby heart gemstone radiating sparkling restorative healing sparkles, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant glowing pink ruby colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'eff_thorns': {
        'name': 'Efek duri pembalas.png',
        'prompt': (
            'clean 3d voxel art icon of a circular ring of twisting dark green briar bramble vines covered with sharp wooden thorns and red rosebuds, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant thorny vine colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },

    # 8. HUD & Panel Headers
    'ui_coin': {
        'name': 'Tombol koin.png',
        'prompt': (
            'clean 3d voxel art icon of a stack of three shiny golden coins with a star emboss engraved on the top coin, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant treasure gold colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'ui_hp': {
        'name': 'Tombol darah.png',
        'prompt': (
            'clean 3d voxel art icon of a plump glossy crimson red heart with a soft specular shine highlight, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant blood red colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'ui_stam': {
        'name': 'Tombol stamina.png',
        'prompt': (
            'clean 3d voxel art icon of a crackling bright yellow energy lightning bolt with electric sparks, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant electric yellow colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'ui_hunger': {
        'name': 'Tombol lapar.png',
        'prompt': (
            'clean 3d voxel art icon of a juicy grilled drumstick with a bone and roasted golden brown crispy skin, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, appetizing roast colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'ui_scroll': {
        'name': 'Tombol gulungan quest.png',
        'prompt': (
            'clean 3d voxel art icon of an unrolled parchment scroll quest paper with rolled ends and a red wax seal, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, warm parchment colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'ui_party': {
        'name': 'Tombol party.png',
        'prompt': (
            'clean 3d voxel art icon of two friendly adventurer companions standing side by side, one with a green tunic and one with blue armor, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant character colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'ui_team': {
        'name': 'Tombol rekan.png',
        'prompt': (
            'clean 3d voxel art icon of a sturdy handshake between two blocky adventurer arms with leather gauntlets, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, warm leather colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'ui_shop': {
        'name': 'Tombol toko.png',
        'prompt': (
            'clean 3d voxel art icon of a small market stall shop with a striped red and white awning canopy and wooden counter, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant market colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'ui_altar': {
        'name': 'Tombol altar.png',
        'prompt': (
            'clean 3d voxel art icon of a mystical floating ritual altar crystal orb glowing purple with arcane runes orbiting, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, mystical purple glow colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'music': {
        'name': 'Musik.png',
        'prompt': (
            'clean 3d voxel art icon of glowing musical eighth notes beamed together, vibrant cyan and golden yellow colors with floating melody sparkles, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'language': {
        'name': 'Bahasa.png',
        'prompt': (
            'clean 3d voxel art icon of a planetary earth globe sphere showing green voxel continents and deep blue voxel oceans with latitude grid lines, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant globe earth colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'sfx': {
        'name': 'Efek Suara.png',
        'prompt': (
            'clean 3d voxel art icon of a loudspeaker megaphone sound speaker with concentric curved sound wave arcs radiating outwards, bright yellow and orange colors, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant sound speaker colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'controller': {
        'name': 'Pengontrol.png',
        'prompt': (
            'clean 3d voxel art icon of a classic retro video game console controller gamepad with d-pad cross and colorful face buttons, slate dark grey and vibrant cyan red buttons, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'ui_char': {
        'name': 'Tombol karakter.png',
        'prompt': (
            'clean 3d voxel art icon of a single voxel adventurer character standing proudly wearing a feathered cap, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, vibrant adventurer colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'ui_sun': {
        'name': 'Tombol matahari.png',
        'prompt': (
            'clean 3d voxel art icon of a radiant smiling sun with blocky rays in warm golden yellow, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, bright golden colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    },
    'ui_moon': {
        'name': 'Tombol bulan.png',
        'prompt': (
            'clean 3d voxel art icon of a crescent moon with a few tiny stars in soft pale blue and silver, '
            'MagicaVoxel style, isometric 3d perspective, volumetric 3d cubic blocks, simple clean voxel composition, not micro-detailed, '
            'solid cubic voxel shapes, very thin subtle crisp black outline framing the silhouette, soft cel-shading, cool moonlit colors, '
            'plain solid pure white background, no ground shadow, floating isolated, centered, not flat 2d pixel art, not diagonal 2d sprite, not minecraft sprite'
        )
    }
}

def remove_white_bg(img_source, tol=25):
    """Flood-fills from borders to cleanly remove pure white background."""
    if isinstance(img_source, str):
        im = Image.open(img_source).convert('RGBA')
    else:
        im = img_source.convert('RGBA')
        
    arr = np.array(im)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    is_white = (r >= 255 - tol) & (g >= 255 - tol) & (b >= 255 - tol)
    
    h, w = is_white.shape
    visited = np.zeros((h, w), dtype=bool)
    q = deque()
    
    for x in range(w):
        if is_white[0, x]: q.append((0, x)); visited[0, x] = True
        if is_white[h-1, x]: q.append((h-1, x)); visited[h-1, x] = True
    for y in range(h):
        if is_white[y, 0]: q.append((y, 0)); visited[y, 0] = True
        if is_white[y, w-1]: q.append((y, w-1)); visited[y, w-1] = True
        
    while q:
        cy, cx = q.popleft()
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ny, nx = cy + dy, cx + dx
            if 0 <= ny < h and 0 <= nx < w:
                if not visited[ny, nx] and is_white[ny, nx]:
                    visited[ny, nx] = True
                    q.append((ny, nx))
                    
    arr[visited, 3] = 0
    return Image.fromarray(arr)

def register_in_ui_js(item_id):
    """Registers item_id: 'buttons/<item_id>.png' in all ui.js files if not present."""
    line_entry = f"    {item_id}:'buttons/{item_id}.png',\n"
    for js_path in UI_JS_PATHS:
        if not os.path.exists(js_path):
            continue
        with open(js_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if f"'{item_id}':" in content or f"{item_id}:" in content:
            continue
            
        target = "  },\n\n  /* HTML ikon satu item"
        if target in content:
            new_content = content.replace(target, line_entry + target)
        else:
            marker = "    /* drop monster & hewan (Set 5) */\n"
            new_content = content.replace(marker, marker + line_entry)
            
        with open(js_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

def update_ui_buttons():
    """Updates initButtonImages in ui.js to include m-bag, m-craft, m-skill, m-chat, and btn-gear."""
    for js_path in UI_JS_PATHS:
        if not os.path.exists(js_path):
            continue
        with open(js_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if "this.setButtonImage(document.getElementById('m-chat')" not in content:
            target = "this.setButtonImage(document.getElementById('m-skill'),'buttons/skills.png');\n"
            replacement = (
                "this.setButtonImage(document.getElementById('m-skill'),'buttons/skills.png');\n"
                "    this.setButtonImage(document.getElementById('m-chat'),'buttons/chat.png');\n"
                "    this.setButtonImage(document.getElementById('btn-gear'),'buttons/gear.png');\n"
            )
            if target in content:
                content = content.replace(target, replacement)
                with open(js_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"[OK] Mobile action buttons (chat, gear) terpasang di {js_path}")

def deploy_image(pil_img, item_id, indonesian_filename):
    """Deploys the transparent PNG to all 4 game directories."""
    for d in [BUTTON_UI_DIR, BUTTONS_DIR, WWW_BUTTONS_DIR]:
        os.makedirs(d, exist_ok=True)

    p_ui = os.path.join(BUTTON_UI_DIR, indonesian_filename)
    pil_img.save(p_ui, 'PNG')
    
    p_btn = os.path.join(BUTTONS_DIR, f"{item_id}.png")
    pil_img.save(p_btn, 'PNG')
    
    p_www = os.path.join(WWW_BUTTONS_DIR, f"{item_id}.png")
    pil_img.save(p_www, 'PNG')
    
    if os.path.exists(os.path.dirname(ANDROID_BUTTONS_DIR)):
        os.makedirs(ANDROID_BUTTONS_DIR, exist_ok=True)
        p_android = os.path.join(ANDROID_BUTTONS_DIR, f"{item_id}.png")
        pil_img.save(p_android, 'PNG')
        
    print(f"[OK] Sukses menyimpan {indonesian_filename} & {item_id}.png ke seluruh folder!")
    register_in_ui_js(item_id)
    if item_id in ['bag', 'craft', 'skills', 'chat', 'gear']:
        update_ui_buttons()

class FlowAutomator:
    def __init__(self, port=9222):
        opts = Options()
        opts.add_experimental_option('debuggerAddress', f'127.0.0.1:{port}')
        try:
            self.driver = webdriver.Chrome(options=opts)
            print(f"[+] Terhubung ke Chrome (port {port})")
            # Switch to Google Flow tab if not current
            for h in self.driver.window_handles:
                self.driver.switch_to.window(h)
                if 'flow' in self.driver.current_url or 'labs.google' in self.driver.current_url:
                    break
            print(f"[+] Tab aktif: {self.driver.title} ({self.driver.current_url})")
            if '/project/' not in self.driver.current_url:
                try:
                    links = self.driver.find_elements(By.CSS_SELECTOR, "a[aria-label='Open project'], a[aria-label='Buka project'], a[href*='/project/']")
                    if links:
                        print(f"[*] Membuka project: {links[0].get_attribute('href')}")
                        links[0].click()
                        time.sleep(4)
                except Exception as e:
                    print(f"[*] Gagal otomatis membuka project: {e}")
            self.ensure_banana2_settings()
        except Exception as e:
            print(f"[!] Gagal terhubung ke Chrome pada port {port}: {e}")
            print("[!] Pastikan Anda sudah menjalankan 'start_chrome_flow.bat' dan browser Chrome sudah terbuka.")
            sys.exit(1)

    def ensure_banana2_settings(self):
        """Memastikan mode adalah Image, model 🍌 Nano Banana 2, dan aspect ratio 1:1 (crop_square)."""
        try:
            trigger = self.driver.find_element(By.CSS_SELECTOR, "button.settings-trigger-button")
            text = trigger.get_attribute('textContent') or trigger.text or ''
            if 'Banana 2' in text and ('crop_square' in text or '1:1' in text) and 'Lite' not in text:
                print(f"[+] Pengaturan terverifikasi: 🍌 Nano Banana 2 | 1:1 Square Image ({text.strip()})")
                return True

            print(f"[*] Menyesuaikan pengaturan Flow ke Nano Banana 2 (1:1)...")
            self.driver.execute_script("arguments[0].click();", trigger)
            time.sleep(1)

            # 1. Pastikan Mode Image
            for tg in self.driver.find_elements(By.CSS_SELECTOR, "mat-button-toggle"):
                if tg.text.strip().lower().startswith('image'):
                    if 'mat-button-toggle-checked' not in (tg.get_attribute('class') or ''):
                        btn = tg.find_element(By.TAG_NAME, "button")
                        btn.click()
                        time.sleep(1)
                    break

            # 2. Pastikan Model: 🍌 Nano Banana 2
            model_btn = None
            for b in self.driver.find_elements(By.CSS_SELECTOR, "button[aria-label='Select model family']"):
                if 'Nano Banana 2' not in b.text or 'Lite' in b.text:
                    model_btn = b
                    break
            if model_btn:
                model_btn.click()
                time.sleep(0.6)
                for item in self.driver.find_elements(By.CSS_SELECTOR, "[role='menuitem'], .mat-mdc-menu-item"):
                    t = item.text.strip().replace('\n', ' ')
                    if 'Nano Banana 2' in t and 'Lite' not in t:
                        item.click()
                        time.sleep(0.6)
                        break

            # 3. Pastikan Aspect Ratio 1:1
            for tg in self.driver.find_elements(By.CSS_SELECTOR, "mat-button-toggle"):
                if '1:1' in tg.text:
                    if 'mat-button-toggle-checked' not in (tg.get_attribute('class') or ''):
                        btn = tg.find_element(By.TAG_NAME, "button")
                        btn.click()
                        time.sleep(0.5)
                    break

            # Tutup popup pengaturan
            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            time.sleep(0.5)
            trigger = self.driver.find_element(By.CSS_SELECTOR, "button.settings-trigger-button")
            print(f"[+] Pengaturan terpasang: {trigger.text.replace(chr(10), ' ')}")
            return True
        except Exception as e:
            print(f"[*] Info pengaturan: {e}")
            return False

    def generate(self, item_id, indonesian_name=None, custom_prompt=None):
        info = ITEM_PROMPTS.get(item_id, {})
        prompt = custom_prompt or info.get('prompt')
        id_name = indonesian_name or info.get('name') or f"{item_id}.png"
        
        if not prompt:
            print(f"[!] Tidak ada prompt untuk item '{item_id}'.")
            return False

        self.ensure_banana2_settings()
            
        print(f"\n==========================================")
        print(f"[*] Men-generate {item_id} ({id_name}) - 3D Voxel Clean (1:1 Banana 2)")
        print(f"[*] Prompt: {prompt[:80]}...")
        print(f"==========================================")
        
        existing_imgs = self.driver.find_elements(By.TAG_NAME, 'img')
        existing_srcs = set(img.get_attribute('src') for img in existing_imgs if img.get_attribute('src'))
        
        try:
            wait = WebDriverWait(self.driver, 15)
            pm = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div.ProseMirror")))
            pm.click()
        except Exception:
            print("[!] Elemen input editor (div.ProseMirror) tidak ditemukan dalam 15 detik.")
            print("[!] Pastikan Google Flow sudah terbuka di Chrome dan Anda sudah login.")
            return False

        time.sleep(0.2)
        pm.send_keys(Keys.CONTROL + 'a')
        pm.send_keys(Keys.BACKSPACE)
        time.sleep(0.2)
        
        self.driver.execute_script("arguments[0].focus(); document.execCommand('insertText', false, arguments[1]);", pm, prompt)
        time.sleep(1)
        
        try:
            wait = WebDriverWait(self.driver, 10)
            gen_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.generate-icon-button, button[aria-label='Start generation'], button[aria-label='Mulai pembuatan']")))
            gen_btn.click()
        except Exception:
            try:
                gen_btn = self.driver.find_element(By.CSS_SELECTOR, "button.generate-icon-button")
                gen_btn.click()
            except Exception as e:
                print(f"[!] Gagal menemukan/menekan tombol generate: {e}")
                return False

        print("[*] Tombol generate ditekan. Menunggu rendering Nano Banana 2 (1:1)...")
        
        target_src = None
        for sec in range(120):
            time.sleep(1)
            if sec < 10:
                continue
            cur_imgs = self.driver.find_elements(By.TAG_NAME, 'img')
            for img in cur_imgs:
                src = img.get_attribute('src') or ''
                if ('/asb/' in src or 'flow-content.google' in src) and src not in existing_srcs:
                    nw = self.driver.execute_script("return arguments[0].naturalWidth;", img) or 0
                    if nw >= 200:
                        target_src = src
                        break
            if target_src:
                print(f"[+] Gambar selesai di-render dalam {sec+1} detik!")
                break
            if (sec + 1) % 5 == 0:
                print(f"[*] Menunggu render Nano Banana 2... ({sec+1}s)")
                
        if not target_src:
            print("[!] Waktu tunggu render habis.")
            return False
            
        print("[*] Mengunduh gambar kualitas penuh via Fetch...")
        res = self.driver.execute_async_script('''
            var url = arguments[0];
            var cb = arguments[1];
            fetch(url).then(r => r.blob()).then(b => {
                var reader = new FileReader();
                reader.onload = function() { cb(reader.result); };
                reader.readAsDataURL(b);
            }).catch(err => cb('ERROR:' + err));
        ''', target_src)

        if not res or not res.startswith('data:image'):
            print(f"[!] Gagal mengunduh gambar: {res}")
            return False
            
        header, b64data = res.split(',', 1)
        raw_bytes = base64.b64decode(b64data)
        
        import io
        raw_im = Image.open(io.BytesIO(raw_bytes))
        print(f"[+] Gambar berhasil didownload: {raw_im.size} {raw_im.mode}")
        
        print("[*] Menghapus background putih menjadi PNG transparan (RGBA)...")
        trans_im = remove_white_bg(raw_im)
        
        deploy_image(trans_im, item_id, id_name)
        return True

def main():
    parser = argparse.ArgumentParser(description="Google Flow Automated 3D Voxel Clean Icon Generator (Nano Banana 2)")
    parser.add_argument('--item', type=str, help='Item ID dari ITEM_PROMPTS')
    parser.add_argument('--batch', type=str, choices=['items', 'ui', 'furniture', 'shields', 'hud', 'prof', 'effects', 'uiicons', 'castles', 'all'], help='Generate batch of items')
    parser.add_argument('--list', action='store_true', help='List all items and their file status')
    parser.add_argument('--skip-existing', action='store_true', help='Lewati item yang sudah ada di folder buttons/')
    args = parser.parse_args()
    
    if args.list:
        print(f"{'Item ID':<20} {'Filename':<25} {'Exists in buttons/'}")
        print("-" * 60)
        for i_id, d in ITEM_PROMPTS.items():
            btn_path = os.path.join(BUTTONS_DIR, f"{i_id}.png")
            status = "YES" if os.path.exists(btn_path) else "NO"
            print(f"{i_id:<20} {d['name']:<25} {status}")
        return

    bot = FlowAutomator()
    if args.item:
        bot.generate(args.item)
    elif args.batch:
        batches = {
            'items': ['sword_wood', 'hoe', 'sugar_cane', 'sugar', 'cake', 'rope', 'saddle', 'pet_charm', 'log_pass', 'dungeon_changer'],
            'ui': ['build', 'bag', 'skills', 'craft'],
            'furniture': ['f_table', 'f_chair', 'f_bed', 'f_chest', 'f_boat', 'f_board', 'f_workbench', 'f_anvil', 'f_stove', 'f_campfire', 'f_house'],
            'shields': ['shield_wood', 'shield_iron', 'shield_flame', 'shield_venom', 'shield_storm', 'shield_frost', 'shield_dark', 'shield_carapace'],
            'hud': ['chat', 'gear'],
            'prof': ['prof_logging', 'prof_mining', 'prof_harvesting', 'prof_combat', 'prof_blocking', 'prof_crafting', 'prof_cooking', 'prof_farming', 'prof_agility'],
            'effects': ['eff_bleed', 'eff_shock', 'eff_venom', 'eff_frost', 'eff_quake', 'eff_swift', 'eff_guard', 'eff_greed', 'eff_regen', 'eff_thorns'],
            'uiicons': ['ui_coin', 'ui_hp', 'ui_stam', 'ui_hunger', 'ui_scroll', 'ui_party', 'ui_team', 'ui_shop', 'ui_altar', 'ui_char', 'ui_sun', 'ui_moon'],
            'castles': ['f_castle1', 'f_castle2', 'f_castle3', 'f_fence1', 'f_fence2', 'f_fence3', 'f_gate1', 'f_gate2', 'f_gate3'],
            'all': list(ITEM_PROMPTS.keys())
        }
        target_list = batches[args.batch]
        if args.skip_existing:
            target_list = [t for t in target_list if not os.path.exists(os.path.join(BUTTONS_DIR, f"{t}.png"))]
            print(f"[*] Mode --skip-existing aktif. Target tersisa: {len(target_list)} items")
            
        print(f"[*] Memulai batch '{args.batch}' ({len(target_list)} items)...")
        success_count = 0
        for i, item_id in enumerate(target_list, 1):
            print(f"\n>>> [{i}/{len(target_list)}] Memproses: {item_id} <<<")
            ok = bot.generate(item_id)
            if ok:
                success_count += 1
                time.sleep(2)  # Jeda aman antar generasi
            else:
                print(f"[!] Gagal pada item: {item_id}")
                time.sleep(3)
        print(f"\n[DONE] Batch '{args.batch}' selesai! Berhasil: {success_count}/{len(target_list)}")

if __name__ == '__main__':
    main()
