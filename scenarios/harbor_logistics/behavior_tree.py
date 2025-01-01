from enum import Enum
import math
import random
# BT Node List
class BehaviorTreeList:
    CONTROL_NODES = [        
        'Sequence',
        'Fallback'
    ]

    ACTION_NODES = [
        'LocalSensingNode',
        'GoToShip',
        'PickItem',
        'GoToDestination',
        'PlaceItem'
    ]

    CONDITION_NODES = [
        'IsFinishedTask',
        'IsHoldingItem',
        'IsArrivedAtShip',
        'IsArrivedAtDestination'
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

# decision_making_module_path = config['decision_making']['plugin']
# module_path, class_name = decision_making_module_path.rsplit('.', 1)
# decision_making_module = importlib.import_module(module_path)
# decision_making_class = getattr(decision_making_module, class_name)

# Condition nodes
class IsFinishedTask(SyncAction):
    def __init__(self, name, agent):
        super().__init__(name, self._check)        

    def _check(self, agent, blackboard):        
        task_completed = blackboard.get('task_completed', False)        
        if task_completed is False:            
            return Status.FAILURE        
        else:      
            print(f"Agent {agent.agent_id}: Task completed!")   
            blackboard['task_completed'] = False
            blackboard['assigned_task_id'] = None
            return Status.SUCCESS

class IsHoldingItem(SyncAction):
    def __init__(self, name, agent):
        super().__init__(name, self._check)        

    def _check(self, agent, blackboard):        
        assigned_task_id = blackboard.get('assigned_task_id', None)
        if assigned_task_id is None:            
            return Status.FAILURE        
        else:            
            return Status.SUCCESS

class IsArrivedAtShip(SyncAction):
    def __init__(self, name, agent):
        super().__init__(name, self._check)        

    def _check(self, agent, blackboard):        
        status = blackboard.get('status', None)
        if status == "AtShip":            
            blackboard['waypoints'] = None # Reset
            return Status.SUCCESS       
        else:            
            return Status.FAILURE

class IsArrivedAtDestination(SyncAction):
    def __init__(self, name, agent):
        super().__init__(name, self._check)        

    def _check(self, agent, blackboard):        
        status = blackboard.get('status', None)
        if status == "AtDestination":            
            blackboard['waypoints'] = None # Reset
            return Status.SUCCESS       
        else:            
            return Status.FAILURE


# Action nodes
# Local Sensing node
class LocalSensingNode(SyncAction):
    def __init__(self, name, agent):
        super().__init__(name, self._local_sensing)

    def _local_sensing(self, agent, blackboard):        
        blackboard['local_tasks_info'] = agent.get_tasks_nearby(with_completed_task = False)
        blackboard['local_agents_info'] = agent.local_message_receive()

        return Status.SUCCESS

class GoToShip(SyncAction):
    def __init__(self, name, agent):
        super().__init__(name, self._move)
        self.waypoint_follower = WaypointFollower(agent, target_arrive_threshold)
        self.path_planner = PathPlanner(agent)
        self.position_to_pickup = (300, 570)

    def _move(self, agent, blackboard):
        waypoints = blackboard.get('waypoints', None)

        # Path Generation
        if waypoints is None:
            self.path_planner.set_target_position(self.position_to_pickup)
            waypoints = self.path_planner.generate('xy')
            self.waypoint_follower.set_waypoints(waypoints)
            blackboard['waypoints'] = waypoints

        # Waypoint Following
        result = self.waypoint_follower.move()
        if result == Status.SUCCESS:
            blackboard['status'] = "AtShip"
            blackboard['waypoints'] = None # Reset

        return result

class GoToDestination(SyncAction):
    def __init__(self, name, agent):
        super().__init__(name, self._move)
        self.waypoint_follower = WaypointFollower(agent, target_arrive_threshold)
        self.path_planner = PathPlanner(agent)

    def _move(self, agent, blackboard):
        waypoints = blackboard.get('waypoints', None)

        # Path Generation
        if waypoints is None:
            assigned_task_id = blackboard.get('assigned_task_id')  
            position_to_deliver = agent.tasks_info[assigned_task_id].position_to_deliver        
            self.path_planner.set_target_position(position_to_deliver)
            waypoints = self.path_planner.generate('xy')
            blackboard['waypoints'] = waypoints
            self.waypoint_follower.set_waypoints(waypoints)

        # Waypoint Following        
        result = self.waypoint_follower.move()
        if result == Status.SUCCESS:
            blackboard['status'] = "AtDestination"
            blackboard['waypoints'] = None # Reset

        return result

class PathPlanner():
    def __init__(self, agent):
        self.agent = agent
        self.target_position = None

    def set_target_position(self, target_position):
        self.target_position = target_position

    def generate(self, option='xy'):
        """
        Generates waypoints following the Manhattan grid, adding waypoints only at turns.
        The `option` parameter controls the order of movement:
        - 'xy' (default): Move in x-direction first, then y-direction.
        - 'yx': Move in y-direction first, then x-direction.
        """
        waypoints = []
        agent_position = self.agent.position

        # Current agent coordinates
        current_x, current_y = agent_position
        # Target coordinates
        target_x, target_y = self.target_position

        if option == 'xy':
            # Move in x-direction first, then y-direction
            if current_x != target_x:
                waypoints.append((target_x, current_y))
            if current_y != target_y:
                waypoints.append((target_x, target_y))
        elif option == 'yx':
            # Move in y-direction first, then x-direction
            if current_y != target_y:
                waypoints.append((current_x, target_y))
            if current_x != target_x:
                waypoints.append((target_x, target_y))

        return waypoints
    




class WaypointFollower():
    def __init__(self, agent, target_arrive_threshold):
        self.next_waypoint_index = 0  # Initialize the index for the next waypoint
        self.waypoints = None
        self.agent = agent
        self.target_arrive_threshold = target_arrive_threshold

    def reset(self):
        self.next_waypoint_index = 0
        self.waypoints = None

    def set_waypoints(self, waypoints):
        self.waypoints = waypoints

    def move(self):

        agent_position = self.agent.position
        next_waypoint = self.waypoints[self.next_waypoint_index]
        # Calculate the Euclidean distance to the next waypoint
        distance = math.sqrt((next_waypoint[0] - agent_position[0])**2 + 
                             (next_waypoint[1] - agent_position[1])**2)

        if distance < self.target_arrive_threshold:
            self.next_waypoint_index += 1  # Move to the next waypoint
            if self.next_waypoint_index >= len(self.waypoints):
                self.reset()
                return Status.SUCCESS  # Return SUCCESS when all waypoints are visited

        self.agent.follow(next_waypoint)  # Command the agent to follow the current waypoint

        return Status.RUNNING  # Keep RUNNING if not all waypoints have been visited







class PickItem(SyncAction):
    def __init__(self, name, agent):
        super().__init__(name, self._action)

    def _action(self, agent, blackboard):
        unassigned_tasks = agent.get_unassigned_tasks()
        if len(unassigned_tasks) == 0: # TODO: 모든 job 끝나면 일단 Pick-up position에서 대기
            return Status.FAILURE
        
        # assigned_task = random.choice(unassigned_tasks)
        assigned_task = unassigned_tasks[-1] # Pick the last (화면 렌더링과 연관)
        assigned_task.set_assigned_to(agent.agent_id)
        agent.set_assigned_task_id(assigned_task.task_id)
        blackboard['assigned_task_id'] = agent.assigned_task_id

        agent.task_color = assigned_task.color
        agent.update_image()

        return Status.SUCCESS


class PlaceItem(SyncAction):
    def __init__(self, name, agent):
        super().__init__(name, self._action)

    def _action(self, agent, blackboard):
        agent.tasks_info[agent.assigned_task_id].set_done()
        agent.set_assigned_task_id(None)
        blackboard['assigned_task_id'] = None

        agent.task_color = None
        agent.update_image()

        return Status.SUCCESS
    