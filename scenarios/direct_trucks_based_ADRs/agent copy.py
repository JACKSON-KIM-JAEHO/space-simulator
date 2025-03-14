import pygame
import math
import copy
import os
from modules.utils import config, generate_positions 
from modules.base_agent import BaseAgent

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
ASSETS_DIR = os.path.join(PROJECT_ROOT, 'assets')
DRONE_DIR = os.path.join(ASSETS_DIR, 'drone')
TRUCK_DIR = os.path.join(ASSETS_DIR, 'car')

drone_image_path_1 = os.path.join(DRONE_DIR, 'drone_1.png')
drone_image_path_2 = os.path.join(DRONE_DIR, 'drone_2.png')
drone_image_path_3 = os.path.join(DRONE_DIR, 'drone_3.png')
truck_image_path = os.path.join(TRUCK_DIR, 'white.png')

drone_1_image = pygame.image.load(drone_image_path_1)
drone_2_image = pygame.image.load(drone_image_path_2)
drone_3_image = pygame.image.load(drone_image_path_3)
truck_image = pygame.image.load(truck_image_path)

# Load agent configuration
work_rate = config['agents']['work_rate']

# Load behavior tree
behavior_tree_xml = f"{os.path.dirname(os.path.abspath(__file__))}/{config['agents']['behavior_tree_xml']}"


class Agent(BaseAgent):
    def __init__(self, agent_id, position, tasks_info):
        super().__init__(agent_id, position, tasks_info)
        self.work_rate = work_rate
        self.visible = True
        self.task_amount_done = 0.0
        self.reached_depot_point = False
        self.truck_location = False
        self.task_location = False
        self.dropofflocation = False
        self.depot_location= False
        self.assigned_dropoff_location_id = None
        self.blackboard = {}

    def move_to_target(self, target_position): #base의 follow
        if (self.position - target_position).length() <= 1.0:
            return True
        direction = (target_position - self.position).normalize()
        self.position += direction
        return False
    
    def is_at_task_location(self): #함수 하나로
        return (self.position - self.task_location).length() < 1.0
    
    def is_at_dropoff(self):
        return (self.position - self.dropofflocation).length() < 1.0

    def is_at_depot(self):
        return (self.position - self.depot_location).length() < 1.0

  
    def set_task_id(self, task_id):
        self.task_id = task_id
        self.assigned_task_id = task_id

    def draw(self):
           pass

    def update_task_mission_status(self, task_point, target_arrive_threshold):
        self.reached_task_point = (task_point - self.position).length() <= target_arrive_threshold # 이것은 왜 구체적인 숫자로 안 했을까?

    def update_dropoff_mission_status(self, dropofflocation, target_arrive_threshold):
        self.reached_dropofflocation = (dropofflocation - self.position).length() <= target_arrive_threshold

    def update_depot_mission_status(self, depot_point, target_arrive_threshold):
         self.reached_depot_point = (depot_point - self.position).length() <= target_arrive_threshold

class Drone(Agent):
    def __init__(self, agent_id, position, tasks_info):
        super().__init__(agent_id, position, tasks_info)
        self.drone_images = [
            drone_1_image, drone_2_image, drone_3_image
            # Add more images for smoother rotation if available
        ]
        self.blade_image_index = 0
        self.frame_count = 0
        self.rotation_speed = 5  # Adjust for how fast you want the blades to rotate
        self.task_completed = False
        self.truck_location = position #포인터 또는 값을 준다. 경계가 헷갈릴 수 있음음 copy.deepcopy #다시보자
        self.is_deployed = False

        '''
        드론이 해야할 역할
            1. drop_item
            2. is_at_task_location
            3. is_at_truck
            4. dock_to_truck
            5. release_from_truck
            6. is_truck_assigned
            7. move_to_truck_location
        '''
    
    def drop_item(self):
        self.task_completed = True


    def is_at_truck(self):
        return (self.position - self.truck_location).length() < 1.0

    def dock_to_truck(self):
        self.is_deployed = False
        self.position = self.truck_location #여기서는 이것이 포인터로 받아야 의미 있기에 확인 할 것
    
    def release_from_truck(self):
        if not self.is_deployed:  # 한 번만 실행되도록
            self.is_deployed = True
            deploy_offset = pygame.Vector2(10, 10)  # 트럭에서 떨어질 거리 --> 아주 조금만 떨어지게 하기 분리 느낌 나게게
            self.position = self.truck_location + deploy_offset
    
    def is_truck_assigned(self):
        return self.truck_location is not None #오류 발생 가능성 있음음


    def draw(self, screen, paused = False):
           
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

    
class Truck(Agent):
    def __init__(self, agent_id, position, tasks_info):
        super().__init__(agent_id, position, tasks_info)
        self.drone = []
        self.dropoff_locations = []  # 🚀 초기화 추가

    def draw(self, screen):
        resized_truck_image = pygame.transform.scale(truck_image, (100,100))
        truck_rect = resized_truck_image.get_rect(center=(self.position.x, self.position.y))
        screen.blit(resized_truck_image, truck_rect.topleft)

    '''
    트럭이 해야할 역할
        1. assign_drone
        2. is_at_dropoff
        3. is_at_depot
        4. activate_drone
        5. calculate_dropoff
        6. no_more_dropoff

        assign_drone - 각 트럭에 드론 배정 
    '''
    def no_more_dropoff(self):
        return len(self.dropoff_locations) == 0
    
    def assign_drone(self, drone):
        self.drones.append(drone)
        drone.truck_location = self.position


    def activate_drone(self):
        if self.drone:
            self.drone.release_from_truck()
            self.drone.start_mission()
            '''
            start mission 구현 필요요
            '''

    def calculate_dropoff(self): #필요한가?
        self.dropoff_locations = [pygame.Vector2(500, 500), pygame.Vector2(600, 600)]  # 여러 개 설정 가능
        return self.dropoff_locations[0]  # 첫 번째 dropoff 반환
    
    def get_next_dropoff(self):
        if self.dropoff_locations:
            next_dropoff = self.dropoff_locations.pop(0)  # 첫 번째 dropoff 선택
            self.assigned_dropoff_location_id = id(next_dropoff)  # 🚀 ID 할당
            return next_dropoff
        return None

def generate_agents(tasks_info, depot_location=(700, 500)):
    """
    트럭과 드론을 생성하고 배치하는 함수
    """
    truck_quantity = config['agents']['truck_quantity']
    drone_quantity = config['agents']['drone_quantity']
    drones_per_truck = config['agents'].get('drones_per_truck')
    agents = []  # 트럭과 드론을 담을 리스트

    # 트럭 생성
    trucks = [
        Truck(truck_id, pygame.Vector2(depot_location), tasks_info)
        for truck_id in range(truck_quantity)
    ]
    agents.extend(trucks)

    # 드론 생성 및 트럭 할당
    drones = []
    for drone_id in range(drone_quantity):
        assigned_truck = trucks[drone_id % truck_quantity]  # 순환 방식으로 트럭 배정
        drone_position = assigned_truck.position  # 트럭과 같은 위치에서 시작

        drone = Drone(drone_id, drone_position, tasks_info)
        assigned_truck.assign_drone(drone)  # 트럭에 드론 추가
        drone.truck_location = assigned_truck.position  # 트럭 위치 저장 #TODO 위에 assign_drone 확인인
        drone.is_deployed = False  # 트럭에 있을 때는 deploy 상태 아님

        drones.append(drone)

    agents.extend(drones)  # 트럭과 드론을 모두 리스트에 추가

    # 행동 트리 생성 및 글로벌 정보 설정
    for agent in agents:
        agent.set_global_info_agents(agents)
        agent.create_behavior_tree(behavior_tree_xml)

    return agents