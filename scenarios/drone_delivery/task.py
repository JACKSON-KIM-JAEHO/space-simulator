import pygame
import random
from modules.utils import config, generate_positions, generate_task_colors
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  # 상위 폴더로 이동
ASSETS_DIR = os.path.join(PROJECT_ROOT, 'assets')
IMAGE_DIR = os.path.join(ASSETS_DIR, 'image')
POINT_DIR = os.path.join(IMAGE_DIR, 'point')

start_image_path = os.path.join(POINT_DIR, 'pickup_point.png')
end_image_path = os.path.join(POINT_DIR, 'dropoff_point.png')

start_image = pygame.image.load(start_image_path).convert_alpha()
end_image = pygame.image.load(end_image_path).convert_alpha()

resized_start_image = pygame.transform.scale(start_image, (65, 65))
resized_end_image = pygame.transform.scale(end_image, (80, 80))

dynamic_task_generation = config['tasks'].get('dynamic_task_generation', {})
max_generations = dynamic_task_generation.get('max_generations', 0) if dynamic_task_generation.get('enabled', False) else 0
tasks_per_generation = dynamic_task_generation.get('tasks_per_generation', 0) if dynamic_task_generation.get('enabled', False) else 0

task_colors = generate_task_colors(config['tasks']['quantity'] + tasks_per_generation*max_generations)

sampling_freq = config['simulation']['sampling_freq']
sampling_time = 1.0 / sampling_freq  # in seconds
class Task:
    def __init__(self, task_id, position, color, is_start = True):
        self.task_id = task_id
        self.position = pygame.Vector2(position)
        self.amount = random.uniform(config['tasks']['amounts']['min'], config['tasks']['amounts']['max'])
        self.radius = self.amount / config['simulation']['task_visualisation_factor']
        self.completed = False
        self.color = task_colors.get(self.task_id, (0, 0, 0))  # Default to black if task_id not found
        self.is_start = is_start
        self.assigned = False

    def set_done(self):
        self.completed = True

    def reduce_amount(self, work_rate):
        self.amount -= work_rate * sampling_time
        if self.amount <= 0:
            self.set_done()

    def draw(self, screen):
        self.radius = self.amount / config['simulation']['task_visualisation_factor']        
        if not self.completed:
            image_rect = resized_start_image.get_rect(center=(self.position.x, self.position.y)) if self.is_start else resized_end_image.get_rect(center=(self.position.x, self.position.y))
            if self.is_start:
                screen.blit(resized_start_image, image_rect.topleft)
            else:
                screen.blit(resized_end_image, image_rect.topleft)

    def draw_task_id(self, screen):
        if not self.completed:
            font = pygame.font.Font(None, 15)
            text_surface = font.render(f"task_id {self.task_id}: {self.amount:.2f}", True, (250, 250, 250))
            screen.blit(text_surface, (self.position[0], self.position[1]))
    def get_pair_task_id(self):
        """ Returns the task_id of the paired task (start for end, and end for start) """
        return self.task_id + 1 if self.is_start else self.task_id - 1
    
def generate_random_color():
        return (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

def generate_tasks(task_quantity=None, task_id_start = 0):
    if task_quantity is None:
        task_quantity = config['tasks']['quantity']        
    task_locations = config['tasks']['locations']

    tasks_positions = generate_positions(task_quantity,
                                        task_locations['x_min'],
                                        task_locations['x_max'],
                                        task_locations['y_min'],
                                        task_locations['y_max'],
                                        radius=task_locations['non_overlap_radius'])

    # Initialize tasks
    tasks = []
    for idx in range(0, len(tasks_positions), 2):
        start_position = tasks_positions[idx]
        end_position = tasks_positions[idx + 1]
        color = generate_random_color()
        tasks.append(Task(idx + task_id_start, start_position, color, is_start=True))  #start point
        tasks.append(Task(idx + task_id_start + 1, end_position, color, is_start=False))  #final point
    
    return tasks
