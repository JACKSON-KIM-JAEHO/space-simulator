import pygame
import random
from modules.utils import config, generate_positions, generate_task_colors
dynamic_task_generation = config['tasks'].get('dynamic_task_generation', {})
max_generations = dynamic_task_generation.get('max_generations', 0) if dynamic_task_generation.get('enabled', False) else 0
tasks_per_generation = dynamic_task_generation.get('tasks_per_generation', 0) if dynamic_task_generation.get('enabled', False) else 0

# TODO: 아래 Refactoring 필요
screen_width = config['simulation']['screen_width']
task_colors = ['red', 'blue', 'yellow']
container_width = 80
container_height = 150
container_spacing = 150  # 간격 값을 150으로 설정
# Define container positions with updated spacing
container_positions = [(screen_width - 100, 110 + i * (container_height + container_spacing)) for i in range(len(task_colors))]
container_images = {
    'red': pygame.image.load('scenarios/harbor_logistics/assets/tasks/red.png'),
    'blue': pygame.image.load('scenarios/harbor_logistics/assets/tasks/blue.png'),
    'yellow': pygame.image.load('scenarios/harbor_logistics/assets/tasks/yellow.png')
}


sampling_freq = config['simulation']['sampling_freq']
sampling_time = 1.0 / sampling_freq  # in seconds
class Task:
    def __init__(self, task_id, position):
        self.task_id = task_id
        self.position = pygame.Vector2(position)
        self.amount = random.uniform(config['tasks']['amounts']['min'], config['tasks']['amounts']['max'])
        self.radius = self.amount / config['simulation']['task_visualisation_factor']
        self.completed = False
        self.assigned_to = None
        random_index = random.randrange(len(task_colors))
        self.color = task_colors[random_index]
        self.position_to_deliver = container_positions[random_index]
        # container 크기로 이미지를 조정
        container_width = 35
        container_height = 50        
        self.image = pygame.transform.scale(container_images[self.color], (container_width, container_height))

    def set_assigned_to(self, agent_id):
        self.assigned_to = agent_id

    def set_done(self):
        self.completed = True

    def reduce_amount(self, work_rate):
        self.amount -= work_rate * sampling_time
        if self.amount <= 0:
            self.set_done()

    def draw(self, screen):
        if self.assigned_to is None:
            screen.blit(self.image, (self.position[0] - container_width // 2, self.position[1] - container_height // 2))            

    def draw_task_id(self, screen):
        if not self.completed:
            font = pygame.font.Font(None, 15)
            text_surface = font.render(f"task_id {self.task_id}: {self.amount:.2f}", True, (250, 250, 250))
            screen.blit(text_surface, (self.position[0], self.position[1]))

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
    tasks = [Task(idx + task_id_start, pos) for idx, pos in enumerate(tasks_positions)]
    return tasks
