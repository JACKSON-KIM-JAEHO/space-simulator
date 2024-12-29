from enum import Enum
import math
import random
import pygame
# BT Node List
class BehaviorTreeList:
    CONTROL_NODES = [        
        'Sequence',
        'Fallback'
    ]

    ACTION_NODES = [
        'LocalSensingNode',
        'DecisionMakingNode',
        'TaskExecutingNode',
        'ExplorationNode',
        'CheckingitemsNode',
        'DeliveryexecutingNode',
        'RightplacecheckingNode',
        'DropoffexecutingNode',
        'CheckingnomoreTask',
        'GatheringNode',
    ]


# Status enumeration for behavior tree nodes
class Status(Enum):
    SUCCESS = 1
    FAILURE = 2
    RUNNING = 3

# Base class for all behavior tree nodes
class Node:
    def __init__(self, name):
        self.name = name

    async def run(self, agent, blackboard):
        raise NotImplementedError

# Sequence node: Runs child nodes in sequence until one fails
class Sequence(Node):
    def __init__(self, name, children):
        super().__init__(name)
        self.children = children

    async def run(self, agent, blackboard):
        for child in self.children:
            status = await child.run(agent, blackboard)
            if status == Status.RUNNING:
                continue
            if status != Status.SUCCESS:
                return status
        return Status.SUCCESS

# Fallback node: Runs child nodes in sequence until one succeeds
class Fallback(Node):
    def __init__(self, name, children):
        super().__init__(name)
        self.children = children

    async def run(self, agent, blackboard):
        for child in self.children:
            status = await child.run(agent, blackboard)
            if status == Status.RUNNING:
                continue
            if status != Status.FAILURE:
                return status
        return Status.FAILURE

# Synchronous action node
class SyncAction(Node):
    def __init__(self, name, action):
        super().__init__(name)
        self.action = action

    async def run(self, agent, blackboard):
        result = self.action(agent, blackboard)
        blackboard[self.name] = result
        return result

# Load additional configuration and import decision-making class dynamically
import importlib
from modules.utils import config
from plugins.my_decision_making_plugin import *
target_arrive_threshold = config['tasks']['threshold_done_by_arrival']
task_locations = config['tasks']['locations']
sampling_freq = config['simulation']['sampling_freq']
sampling_time = 1.0 / sampling_freq  # in seconds
agent_max_random_movement_duration = config.get('agents', {}).get('random_exploration_duration', None)

decision_making_module_path = config['decision_making']['plugin']
module_path, class_name = decision_making_module_path.rsplit('.', 1)
decision_making_module = importlib.import_module(module_path)
decision_making_class = getattr(decision_making_module, class_name)

# Local Sensing node
class LocalSensingNode(SyncAction):
    def __init__(self, name, agent):
        super().__init__(name, self._local_sensing)

    def _local_sensing(self, agent, blackboard):        
        blackboard['local_tasks_info'] = agent.get_tasks_nearby(with_completed_task = False)
        blackboard['local_agents_info'] = agent.local_message_receive()

        return Status.SUCCESS
    
# Decision-making node
class DecisionMakingNode(SyncAction):
    def __init__(self, name, agent):
        super().__init__(name, self._decide)
        self.decision_maker = MyDecisionMakingClass(agent)

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
        self.gathering_mode = False 
        self.gathering_point = pygame.Vector2(700, 500) # gathering point(700, 500)

    def _gather_to_point(self, agent, blackboard):
        if agent.assigned_task_id is not None and agent.tasks_info[agent.assigned_task_id].completed:
            self.gathering_mode = True

        if self.gathering_mode:
            distance_to_target = (self.gathering_point - agent.position).length()
            if distance_to_target > target_arrive_threshold:
                agent.follow(self.gathering_point)
                return Status.RUNNING 
            
            agent.position = self.gathering_point
            agent.reset_movement() 
            agent.visible = False # make dissapear when agents are arrived at the final point
            self.gathering_mode = False
            return Status.SUCCESS
        
        return Status.FAILURE 
    
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
