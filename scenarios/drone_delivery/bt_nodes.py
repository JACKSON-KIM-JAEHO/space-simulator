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

# TODO: 나중에 변경 필요
from scenarios.drone_delivery.decision_making.simple import MyDecisionMakingClass as decision_making_class

# Decision-making node -- Override # TODO - 이것도 원래 template에 맞지 않는 form임. 변경 필요
class DecisionMakingNode(SyncAction):
    def __init__(self, name, agent):
        super().__init__(name, self._decide)
        self.decision_maker = decision_making_class(agent)

    def _decide(self, agent, blackboard):
        assigned_task_id = self.decision_maker.decide(blackboard)
        if assigned_task_id is None:
            return Status.FAILURE
        agent.set_assigned_task_id(assigned_task_id)
        return Status.SUCCESS
    
#Checking items Node
class CheckingitemsNode(SyncAction):
    def __init__(self, name, agent):
        super().__init__(name, self._check_item)

    def _check_item(self, agent, blackboard):
        task_id = blackboard.get('assigned_task_id')
        if task_id is None:
            return Status.FAILURE
        
        task = agent.tasks_info[task_id]

        if task and task.is_start:
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

        if task and task.is_start and not task.completed:
            agent_position = agent.position
            target_position = task.position
            distance = math.sqrt((target_position[0] - agent_position[0])**2 + (target_position[1] - agent_position[1])**2)
        

            if distance < task.radius + target_arrive_threshold:
                task.reduce_amount(agent.work_rate)
                
                if task.completed:
                    end_task_id = task.get_pair_task_id()
                    blackboard['assigned_task_id'] = end_task_id
                    return Status.SUCCESS
                else:
                    return Status.RUNNING
            else:
                agent.follow(target_position)
                return Status.RUNNING
        return Status.FAILURE

#Right place checking Node
class RightplacecheckingNode(SyncAction):
    def __init__(self, name, agent):
        super().__init__(name, self._check_place)

    def _check_place(self, agent, blackboard):
        task_id = blackboard.get('assigned_task_id')
        if task_id is None:
            return Status.FAILURE
        
        task = agent.tasks_info[task_id]

        if task and not task.is_start:
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

        if task and not task.is_start and not task.completed:
            agent_position = agent.position
            target_position = task.position
            distance = math.sqrt((target_position[0] - agent_position[0])**2 + (target_position[1] - agent_position[1])**2)


            if distance < task.radius + target_arrive_threshold:
                task.reduce_amount(agent.work_rate)

                if task.completed:
                    blackboard['assigned_task_id'] = None
                    blackboard['end_task_id'] = None


                    return Status.SUCCESS
                else:
                    return Status.RUNNING
            else:
                agent.follow(target_position)
                return Status.RUNNING

        return Status.FAILURE

class CheckingnomoreTask(SyncAction):
    def __init__(self, name, agent):
        super().__init__(name, self._check_no_more_tasks)

    def _check_no_more_tasks(self, agent, blackboard):
        available_tasks = [
            task for task in agent.tasks_info
            if task.is_start and not task.completed and not task.assigned
        ]

        if not available_tasks:
            return Status.SUCCESS
        else:
            return Status.FAILURE
            
class GatheringNode(SyncAction):
    def __init__(self, name, agent):
        super().__init__(name, self._gather_to_point)
        #self.gathering_mode = False 
        self.gathering_point = pygame.Vector2(700, 500) # gathering point(700, 500)
        self.target_arrive_threshold = target_arrive_threshold

    def _gather_to_point(self, agent, blackboard):
        distance_to_target = (self.gathering_point - agent.position).length()
        if distance_to_target > self.target_arrive_threshold:
            agent.follow(self.gathering_point)
            return Status.RUNNING
        
        agent.position = self.gathering_point
        agent.reset_movement() 
        agent.visible = False # make dissapear when agents are arrived at the final point
        self.gathering_mode = False
        return Status.SUCCESS

    
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
