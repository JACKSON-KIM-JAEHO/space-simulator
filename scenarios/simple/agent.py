import pygame
import math
import copy
import os
from modules.behavior_tree import *
from modules.utils import config, generate_positions 
from modules.base_agent import BaseAgent
from modules.task import task_colors

# Load agent configuration (Scenario Specific)
work_rate = config['agents']['work_rate']

# Load behavior tree
behavior_tree_xml = f"{os.path.dirname(os.path.abspath(__file__))}/{config['agents']['behavior_tree_xml']}"

class Agent(BaseAgent):
    def __init__(self, agent_id, position, tasks_info):
        super().__init__(agent_id, position, tasks_info)
        self.work_rate = work_rate

        self.assigned_task_id = None         # Local decision-making result.
        self.planned_tasks = []              # Local decision-making result.
        
        self.task_amount_done = 0.0        


        self.image = pygame.image.load('scenarios/harbor_logistics/assets/Agents/agent.png')  # 기본 이미지
        self.image = pygame.transform.scale(self.image, (50, 50))  # 크기 조정
        self.task_color = None  # 현재 운반 중인 task 색상 (없으면 None)

    def update_image(self):
        """현재 상태에 따라 이미지를 업데이트"""
        if self.task_color == 'red':
            self.image = pygame.image.load('scenarios/harbor_logistics/assets/Agents/agent_with_red_container.png')
        elif self.task_color == 'blue':
            self.image = pygame.image.load('scenarios/harbor_logistics/assets/Agents/agent_with_blue_container.png')
        elif self.task_color == 'yellow':
            self.image = pygame.image.load('scenarios/harbor_logistics/assets/Agents/agent_with_yellow_container.png')
        else:
            self.image = pygame.image.load('scenarios/harbor_logistics/assets/Agents/agent.png')  # 기본 이미지

        # 이미지 크기 조정
        self.image = pygame.transform.scale(self.image, (50, 50))





       

    def draw(self, screen):
        size = 10
        angle = self.rotation

        # Calculate the triangle points based on the current position and angle
        p1 = pygame.Vector2(self.position.x + size * math.cos(angle), self.position.y + size * math.sin(angle))
        p2 = pygame.Vector2(self.position.x + size * math.cos(angle + 2.5), self.position.y + size * math.sin(angle + 2.5))
        p3 = pygame.Vector2(self.position.x + size * math.cos(angle - 2.5), self.position.y + size * math.sin(angle - 2.5))

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
