#!/usr/bin/env python3
"""
Create Minecraft heart sprite sheet
Hearts are 9x9 pixels in Minecraft
"""
from PIL import Image, ImageDraw
import os

# Create sprite sheet: 9x9 pixels per heart
# Layout: Full, Half, Empty (in a row)
SPRITE_SIZE = 9
SHEET_WIDTH = SPRITE_SIZE * 3  # 3 hearts side by side
SHEET_HEIGHT = SPRITE_SIZE

def create_heart_sprite(draw, x_offset, y_offset, fill_type='full'):
    """Draw a Minecraft-style heart sprite (pixel-perfect 9x9)"""
    # Minecraft heart colors
    fill_color = (220, 0, 0)  # Minecraft red #DC0000
    outline_color = (0, 0, 0)  # Black outline
    
    # Pixel-perfect Minecraft heart pattern (9x9 grid)
    # Row 0:     . . # # . # # . .
    # Row 1:     . # # # # # # # .
    # Row 2:     # # # # # # # # #
    # Row 3:     # # # # # # # # #
    # Row 4:     . # # # # # # # .
    # Row 5:     . . # # # # # . .
    # Row 6:     . . . # # # . . .
    # Row 7:     . . . . # . . . .
    # Row 8:     . . . . . . . . .
    
    # Define heart pixels as (x, y) coordinates
    heart_pixels = [
        # Top curves (rows 0-1)
        (2, 0), (3, 0), (5, 0), (6, 0),
        (1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (7, 1),
        # Main body (rows 2-4)
        (0, 2), (1, 2), (2, 2), (3, 2), (4, 2), (5, 2), (6, 2), (7, 2), (8, 2),
        (0, 3), (1, 3), (2, 3), (3, 3), (4, 3), (5, 3), (6, 3), (7, 3), (8, 3),
        (1, 4), (2, 4), (3, 4), (4, 4), (5, 4), (6, 4), (7, 4),
        # Bottom (rows 5-7)
        (2, 5), (3, 5), (4, 5), (5, 5), (6, 5),
        (3, 6), (4, 6), (5, 6),
        (4, 7),
    ]
    
    # Outline pixels (black border)
    outline_pixels = [
        # Top outline
        (2, 0), (3, 0), (5, 0), (6, 0),
        (1, 1), (7, 1),
        (0, 2), (8, 2),
        (0, 3), (8, 3),
        (1, 4), (7, 4),
        (2, 5), (6, 5),
        (3, 6), (5, 6),
        (4, 7),
    ]
    
    if fill_type == 'full':
        # Fill all heart pixels
        for x, y in heart_pixels:
            draw.point((x_offset + x, y_offset + y), fill=fill_color)
        # Draw outline
        for x, y in outline_pixels:
            draw.point((x_offset + x, y_offset + y), fill=outline_color)
            
    elif fill_type == 'half':
        # Fill left half only (x < 4.5, which is x <= 4)
        left_half_pixels = [(x, y) for x, y in heart_pixels if x <= 4]
        for x, y in left_half_pixels:
            draw.point((x_offset + x, y_offset + y), fill=fill_color)
        # Draw full outline
        for x, y in outline_pixels:
            draw.point((x_offset + x, y_offset + y), fill=outline_color)
            
    else:  # empty/container
        # Only draw outline
        for x, y in outline_pixels:
            draw.point((x_offset + x, y_offset + y), fill=outline_color)

def create_sprite_sheet():
    """Create a sprite sheet with all heart variants"""
    # Create image with transparency
    img = Image.new('RGBA', (SHEET_WIDTH, SHEET_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw full heart (left)
    create_heart_sprite(draw, 0, 0, 'full')
    
    # Draw half heart (middle)
    create_heart_sprite(draw, SPRITE_SIZE, 0, 'half')
    
    # Draw empty heart (right)
    create_heart_sprite(draw, SPRITE_SIZE * 2, 0, 'empty')
    
    return img

def create_individual_sprites():
    """Create individual sprite files"""
    img = Image.new('RGBA', (SPRITE_SIZE, SPRITE_SIZE), (0, 0, 0, 0))
    
    for heart_type in ['full', 'half', 'empty']:
        draw = ImageDraw.Draw(img)
        img.paste((0, 0, 0, 0), (0, 0, SPRITE_SIZE, SPRITE_SIZE))  # Clear
        create_heart_sprite(draw, 0, 0, heart_type)
        img.save(f'{heart_type}.png')
        print(f'Created {heart_type}.png')

if __name__ == '__main__':
    # Create sprite sheet
    sheet = create_sprite_sheet()
    sheet.save('hearts_sprite_sheet.png')
    print('Created hearts_sprite_sheet.png')
    
    # Create individual sprites
    create_individual_sprites()
    
    print('\nAll heart sprites created!')
    print('Files:')
    print('  - hearts_sprite_sheet.png (all variants in one image)')
    print('  - full.png (full heart)')
    print('  - half.png (half heart)')
    print('  - empty.png (empty/container heart)')
