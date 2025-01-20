from enum import Enum
import math
import random
import pygame
from modules.base_bt_nodes import BTNodeList, Status, Node, Sequence, Fallback, SyncAction, LocalSensingNode, DecisionMakingNode

# BT Node List
CUSTOM_ACTION_NODES = [
    'ExplorationNode',
    'CheckingitemsNode',
    'DeliveryexecutingNode',
    'RightplacecheckingNode',
    'DropoffexecutingNode',
    'CheckingnomoreTask',
    'GatheringNode',
]

CUSTOM_CONDITION_NODES = [
]

BTNodeList.ACTION_NODES.extend(CUSTOM_ACTION_NODES)
BTNodeList.CONDITION_NODES.extend(CUSTOM_CONDITION_NODES)



# Scenario-specific Action/Condition Nodes
from modules.utils import config
target_arrive_threshold = config['tasks']['threshold_done_by_arrival']
task_locations = config['tasks']['locations']
sampling_freq = config['simulation']['sampling_freq']
sampling_time = 1.0 / sampling_freq  # in seconds
agent_max_random_movement_duration = config.get('agents', {}).get('random_exploration_duration', None)


class DecisionMakingNode(SyncAction): 
    def __init__(self, name, agent):
        super().__init__(name, self._make_decision)

    def _make_decision(self, agent, blackboard):        
        assigned_task_id = blackboard.get('assigned_task_id')

        # 작업이 이미 할당된 경우
        if assigned_task_id is not None:
            task = agent.tasks_info[assigned_task_id]
            if task.pickup_completed and task.delivery_completed:
                # Pick-up과 Delivery가 완료되었으면 할당 해제
                blackboard['assigned_task_id'] = None
                return Status.SUCCESS
            return Status.RUNNING  # 작업이 진행 중

        # 작업이 할당되지 않은 경우, 새로운 작업 할당
        available_tasks = [
            task for task in agent.tasks_info
            if not task.assigned and not task.delivery_completed
        ]

        if not available_tasks:
            # 할당 가능한 작업이 없으면 실패 반환
            return Status.FAILURE

        # 할당 가능한 작업 중 가장 적합한 작업 선택 (예: 거리 기반)
        optimal_task = self._select_optimal_task(agent, available_tasks)

        # 작업 할당
        optimal_task.assigned = True
        blackboard['assigned_task_id'] = optimal_task.task_id
        return Status.SUCCESS

    def _select_optimal_task(self, agent, tasks):
        """
        거리 기반으로 가장 적합한 작업 선택
        """
        agent_position = agent.position
        return min(
            tasks,
            key=lambda task: math.sqrt(
                (task.pickup_position.x - agent_position.x) ** 2 +
                (task.pickup_position.y - agent_position.y) ** 2
            )
        )

#Checking items Node
class CheckingitemsNode(SyncAction):
    def __init__(self, name, agent):
        super().__init__(name, self._check_item)

    def _check_item(self, agent, blackboard):
        task_id = blackboard.get('assigned_task_id')
        if task_id is None:
            return Status.FAILURE
        
        task = agent.tasks_info[task_id]

        if task and not task.pickup_completed:
            return Status.SUCCESS
        else:
            return Status.FAILURE

# Delivery executing node
class DeliveryexecutingNode(SyncAction):
    def __init__(self, name, agent):
        super().__init__(name, self._execute_task)

    def _execute_task(self, agent, blackboard):
        task_id = blackboard.get('assigned_task_id')

        if task_id is None:
            return Status.FAILURE

        task = agent.tasks_info[task_id]
        agent_position = agent.position

        # Pick-up 단계
        if not task.pickup_completed:
            target_position = task.pickup_position
        # Delivery 단계
        elif not task.delivery_completed:
            target_position = task.delivery_position
        else:
            # 작업 완료
            return Status.SUCCESS

        # 거리 계산
        distance = math.sqrt(
            (target_position.x - agent_position.x) ** 2 +
            (target_position.y - agent_position.y) ** 2
        )

        # 목표 위치 도착 처리
        if distance < task.radius + target_arrive_threshold:
            if not task.pickup_completed:
                task.complete_pickup()  # Pick-up 완료 처리
            elif not task.delivery_completed:
                task.complete_delivery()  # Delivery 완료 처리
                return Status.SUCCESS
        else:
            # 목표 위치로 이동
            agent.follow(target_position)

        return Status.RUNNING

#Right place checking Node
class RightplacecheckingNode(SyncAction):
    def __init__(self, name, agent):
        super().__init__(name, self._check_place)

    def _check_place(self, agent, blackboard):
        task_id = blackboard.get('assigned_task_id')
        if task_id is None:
            return Status.FAILURE
        
        task = agent.tasks_info[task_id]

        if task and not task.pickup_completed:
            return Status.SUCCESS
        elif task and task.pickup_completed and not task.delivery_completed:
            return Status.SUCCESS
        return Status.FAILURE

# Dropoff executing node
class DropoffexecutingNode(SyncAction):
    def __init__(self, name, agent):
        super().__init__(name, self._execute_dropoff)

    def _execute_dropoff(self, agent, blackboard):
        task_id = blackboard.get('assigned_task_id')

        if task_id is None:
            return Status.FAILURE

        task = agent.tasks_info[task_id]

        # Delivery 작업 처리
        if not task.pickup_completed:
            target_position = task.pickup_position
        elif not task.delivery_completed:
            target_position = task.delivery_position
        else:
            # 작업 완료 처리
            task.check_completion()
            return Status.SUCCESS
        
        agent_position = agent.position
        target_position = task.delivery_position
        distance = math.sqrt(
            (target_position.x - agent_position.x) ** 2 +
            (target_position.y - agent_position.y) ** 2
        )

        # Delivery 위치 도착 처리
        if distance < task.radius + target_arrive_threshold:
            task.complete_delivery()  # Delivery 완료 처리
            blackboard['assigned_task_id'] = None  # 작업 해제
            return Status.SUCCESS
        else:
            # 목표 위치로 이동
            agent.follow(target_position)
            
        return Status.RUNNING

class CheckingnomoreTask(SyncAction):
    def __init__(self, name, agent):
        super().__init__(name, self._check_no_more_tasks)

    def _check_no_more_tasks(self, agent, blackboard):
        available_tasks = [
            task for task in agent.tasks_info
            if not task.pickup_completed or not task.delivery_completed
        ]

        if not available_tasks:
            return Status.SUCCESS
        else:
            return Status.FAILURE
            
class GatheringNode(SyncAction):
    def __init__(self, name, agents, total_agents = None):
        super().__init__(name, self._gather_to_point)
        #self.gathering_mode = False 
        self.gathering_point = pygame.Vector2(700, 500) # gathering point(700, 500)
        self.target_arrive_threshold = target_arrive_threshold
        self.total_agents = total_agents
        self.agents = agents
        self.agents_arrived = set()

    def _gather_to_point(self, agent, blackboard):
        agent_id = agent.id
        distance_to_target = (self.gathering_point - agent.position).length()

        if distance_to_target > self.target_arrive_threshold:
            agent.follow(self.gathering_point)
            return Status.RUNNING
        
        self.agents_arrived.add(agent_id)
        agent.position = self.gathering_point
        agent.reset_movement() 
        agent.visible = False # make dissapear when agents are arrived at the final point
        
        if self.total_agents is not None and len(self.agents_arrived) == self.total_agents:
            return Status.SUCCESS  # Mission Complete
        return Status.RUNNING

    
# Exploration node
class ExplorationNode(SyncAction):
    def __init__(self, name, agent):
        super().__init__(name, self._random_explore)
        self.random_move_time = float('inf')
        self.random_waypoint = (0, 0)

    def _random_explore(self, agent, blackboard):
        
        current_position = agent.position
        target_position = self.random_waypoint
        distance_to_target = math.sqrt(
            (target_position[0] - current_position[0])**2 +
            (target_position[1] - current_position[1])**2
        )

        if distance_to_target < 10:
            self.random_move_time = float('inf')
            return Status.SUCCESS

        if self.random_move_time > agent_max_random_movement_duration:
            self.random_waypoint = self.get_random_position(task_locations['x_min'], task_locations['x_max'], task_locations['y_min'], task_locations['y_max'])
            self.random_move_time = 0 # Initialisation

        agent.follow(self.random_waypoint)

        self.random_move_time += sampling_time

        return Status.RUNNING

    def get_random_position(self, x_min, x_max, y_min, y_max):
        pos = (random.randint(x_min, x_max),
                random.randint(y_min, y_max))
        return pos
