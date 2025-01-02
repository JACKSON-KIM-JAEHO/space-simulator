import pygame
import math
import copy
import os
from modules.utils import config, generate_positions 
from modules.base_agent import BaseAgent
from modules.task import task_colors

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__)) 
ASSETS_DIR = os.path.join(PROJECT_ROOT, 'assets')
CAR_DIR = os.path.join(ASSETS_DIR, 'car')
DRONE_DIR = os.path.join(ASSETS_DIR, 'drone')
car_image_path = os.path.join(CAR_DIR, 'white.png')
drone_image_path_1 = os.path.join(DRONE_DIR, 'drone_1.png')
drone_image_path_2 = os.path.join(DRONE_DIR, 'drone_2.png')
drone_image_path_3 = os.path.join(DRONE_DIR, 'drone_3.png')

car_image = pygame.image.load(car_image_path)
drone_1_image = pygame.image.load(drone_image_path_1)
drone_2_image = pygame.image.load(drone_image_path_2)
drone_3_image = pygame.image.load(drone_image_path_3)
# TODO: Error occurs when having `convert_alpah`
# car_image = pygame.image.load(car_image_path).convert_alpha()
# drone_1_image = pygame.image.load(drone_image_path_1).convert_alpha()
# drone_2_image = pygame.image.load(drone_image_path_2).convert_alpha()
# drone_3_image = pygame.image.load(drone_image_path_3).convert_alpha()


# Load agent configuration
work_rate = config['agents']['work_rate']

# Load behavior tree
behavior_tree_xml = f"{os.path.dirname(os.path.abspath(__file__))}/{config['agents']['behavior_tree_xml']}"


class Agent(BaseAgent):
    def __init__(self, agent_id, position, tasks_info):
        super().__init__(agent_id, position, tasks_info)
        self.work_rate = work_rate
        self.decision_maker = None
        self.visible = True


        self.assigned_task_id = None         # Local decision-making result.
        self.planned_tasks = []              # Local decision-making result.

        self.task_amount_done = 0.0
        self.end_task_id = None

        # Load rotating blade images
        self.drone_images = [
            drone_1_image, drone_2_image, drone_3_image
            # Add more images for smoother rotation if available
        ]
        self.blade_image_index = 0
        self.frame_count = 0
        self.rotation_speed = 5  # Adjust for how fast you want the blades to rotate

    def is_near_task(self, task):
        distance = self.position.distance_to(task.position)
        return distance < task.radius + target_arrive_threshold
    
    def set_end_task_id(self, task_id):
        self.end_task_id = task_id
        self.assigned_task_id = task_id


 
    def draw(self, screen):
        if not self.visible:
            return
            
         # Cycling through blade images for animation
        self.frame_count += 1
        if self.frame_count % self.rotation_speed == 0:
            self.blade_image_index = (self.blade_image_index + 1) % len(self.drone_images)

        resized_image = pygame.transform.scale(car_image, (0, 0))
        rotated_image = pygame.transform.rotate(resized_image, -math.degrees(self.rotation))
        
        image_rect = rotated_image.get_rect(center=(self.position.x, self.position.y))
        screen.blit(rotated_image, image_rect.topleft)

        drone_image = self.drone_images[self.blade_image_index]

        resized_blade_image = pygame.transform.scale(drone_image, (50, 45))  # Adjust size here
        rotated_blade_image = pygame.transform.rotate(resized_blade_image, -math.degrees(self.rotation))

        blade_image_rect = rotated_blade_image.get_rect(center=(self.position.x, self.position.y))
        screen.blit(rotated_blade_image, blade_image_rect.topleft)

        # Optionally, draw other elements like the rotating blades on top
        self.update_color()

    def draw_rotating_blades(self, screen):
        """Draws rotating blades with animation"""
        # Update the blade image every few frames to simulate rotation
        self.frame_count += 1
        if self.frame_count % self.rotation_speed == 0:
            self.blade_image_index = (self.blade_image_index + 1) % len(self.drone_images)

        # Get the current blade image
        blade_image = self.drone_images[self.blade_image_index]

        # Rotate the blade image according to the agent's current rotation
        rotated_blade_image = pygame.transform.rotate(blade_image, -math.degrees(self.rotation))
        blade_rect = rotated_blade_image.get_rect(center=(self.position.x, self.position.y))

        # Draw the rotating blade at the agent's position
        screen.blit(rotated_blade_image, blade_rect.topleft)
        
        self.update_color()
        pygame.draw.polygon(screen, self.color, [p1, p2, p3])


    def draw_assigned_task_id(self, screen):
        # Draw assigned_task_id next to agent position
        if len(self.planned_tasks) > 0:
            assigned_task_id_list = [task.task_id for task in self.planned_tasks]
        else:
            assigned_task_id_list = self.assigned_task_id
        text_surface = self.font.render(f"task_id: {assigned_task_id_list}", True, (50, 50, 50))
        screen.blit(text_surface, (self.position[0] + 10, self.position[1]))

    def draw_work_done(self, screen):
        # Draw assigned_task_id next to agent position
        text_surface = self.font.render(f"dist: {self.distance_moved:.1f}", True, (50, 50, 50))
        screen.blit(text_surface, (self.position[0] + 10, self.position[1] + 10))
        text_surface = self.font.render(f"work: {self.task_amount_done:.1f}", True, (50, 50, 50))
        screen.blit(text_surface, (self.position[0] + 10, self.position[1] + 20))


    def draw_path_to_assigned_tasks(self, screen):
        # Starting position is the agent's current position
        start_pos = self.position

        # Define line thickness
        line_thickness = 3  # Set the desired thickness for the lines        
        # line_thickness = 16-4*self.agent_id  # Set the desired thickness for the lines        

        # For Debug
        color_list = [
            (255, 0, 0),  # Red
            (0, 255, 0),  # Green
            (0, 0, 255),  # Blue
            (255, 255, 0),  # Yellow
            (255, 0, 255),  # Magenta
            (0, 255, 255),  # Cyan
            (255, 165, 0),  # Orange
            (128, 0, 128),  # Purple
            (255, 192, 203) # Pink
        ]
                
        # Iterate over the assigned tasks and draw lines connecting them
        for task in self.planned_tasks:
            task_position = task.position
            pygame.draw.line(
                screen,
                # (255, 0, 0),  # Color for the path line (Red)
                color_list[self.agent_id%len(color_list)], 
                (int(start_pos.x), int(start_pos.y)),
                (int(task_position.x), int(task_position.y)),
                line_thickness  # Thickness of the line
            )
            # Update the start position for the next segment
            start_pos = task_position


    def update_color(self):        
        self.color = task_colors.get(self.assigned_task_id, (20, 20, 20))  # Default to Dark Grey if no task is assigned


    def set_assigned_task_id(self, task_id):
        self.assigned_task_id = task_id

    def set_planned_tasks(self, task_list): # This is for visualisation
        self.planned_tasks = task_list    

    def update_task_amount_done(self, amount):
        self.task_amount_done += amount

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
