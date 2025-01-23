import pygame
import math
import copy
import os
from modules.utils import config, generate_positions 
from modules.base_agent import BaseAgent

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__)) 
ASSETS_DIR = os.path.join(PROJECT_ROOT, 'assets')
DRONE_DIR = os.path.join(ASSETS_DIR, 'drone')
drone_image_path_1 = os.path.join(DRONE_DIR, 'drone_1.png')
drone_image_path_2 = os.path.join(DRONE_DIR, 'drone_2.png')
drone_image_path_3 = os.path.join(DRONE_DIR, 'drone_3.png')

drone_1_image = pygame.image.load(drone_image_path_1)
drone_2_image = pygame.image.load(drone_image_path_2)
drone_3_image = pygame.image.load(drone_image_path_3)

# Load agent configuration
work_rate = config['agents']['work_rate']

# Load behavior tree
behavior_tree_xml = f"{os.path.dirname(os.path.abspath(__file__))}/{config['agents']['behavior_tree_xml']}"


class Agent(BaseAgent):
    def __init__(self, agent_id, position, tasks_info):
        super().__init__(agent_id, position, tasks_info)
        self.id = agent_id
        self.work_rate = work_rate
        self.decision_maker = None
        self.visible = True

        self.task_amount_done = 0.0
        self.end_task_id = None
        self.mission_finished = False

        # Load rotating blade images
        self.drone_images = [
            drone_1_image, drone_2_image, drone_3_image
            # Add more images for smoother rotation if available
        ]
        self.blade_image_index = 0
        self.frame_count = 0
        self.default_rotation_speed = 5  # Adjust for how fast you want the blades to rotate, higher number get more faster
        self.rotation_speed = self.default_rotation_speed  # 현재 회전 속도
        #self.rotation_speed = 10  
  
    def set_end_task_id(self, task_id):
        self.end_task_id = task_id
        self.assigned_task_id = task_id
        '''
        task_info = tasks_info.get(task_id, None)
        if task_info:
            task_center = task_info["center"]
            self.target_position = pygame.math.Vector2(task_center["x"], task_center["y"])
            '''

    def draw(self, screen, paused = False):
        if not self.visible:
            return
           
         # Cycling through blade images for animation
        if not paused:
            self.frame_count += 1
            if self.frame_count % self.rotation_speed == 0:
                self.blade_image_index = (self.blade_image_index + 1) % len(self.drone_images)

        drone_image = self.drone_images[self.blade_image_index]

        resized_blade_image = pygame.transform.scale(drone_image, (50, 45))  # Adjust size here
        rotated_blade_image = pygame.transform.rotate(resized_blade_image, -math.degrees(self.rotation))

        blade_image_rect = rotated_blade_image.get_rect(center=(self.position.x, self.position.y))
        screen.blit(rotated_blade_image, blade_image_rect.topleft)

        # Optionally, draw other elements like the rotating blades on top
        # self.update_color()

    def update_mission_status(self, gathering_point, target_arrive_threshold):
        distance_to_gathering_point = (gathering_point - self.position).length()

        if distance_to_gathering_point <= target_arrive_threshold:
            self.mission_finished = True

def generate_agents(tasks_info):
    agent_quantity = config['agents']['quantity']
    agent_locations = config['agents']['locations']

    agents_positions = generate_positions(agent_quantity,
                                      agent_locations['x_min'],
                                      agent_locations['x_max'],
                                      agent_locations['y_min'],
                                      agent_locations['y_max'],
                                      radius=agent_locations['non_overlap_radius'])

    # Initialize agents
    agents = [Agent(idx, pos, tasks_info) for idx, pos in enumerate(agents_positions)]

    # Provide the global info and create behavior tree
    for agent in agents:
        agent.set_global_info_agents(agents)
        agent.create_behavior_tree(behavior_tree_xml)

    return agents
