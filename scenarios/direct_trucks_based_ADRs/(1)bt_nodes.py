from enum import Enum
import math
import random
import pygame
from modules.base_bt_nodes import *

# BT Node List
CUSTOM_ACTION_NODES = [
    'Takeoff',
    'DockToTruck',
    'DropItem',
    'MoveToTaskLocation',
    'AssignTruck',
    'MoveToTruck', #여기까지가 drone
    'ActivateDroneBT',
    'CalculateDropoffLocation',
    'UpdateDropoffLocation',
    'MoveToDepot',
    'MoveToDropoff',
    'WaitForDrone'
]

CUSTOM_CONDITION_NODES = [
     'IsArrivedAtTaskLocation',
     'IsArrivedAtTruck',
     'IsTruckAssigned', #여기까지가 drone
     'IsActivated', #"IsTruckArrviedAtDropoffLocation"이것과 중복으로 쓰여야 하는가? # agent를 트럭과 드론 둘 다 혼용에서 어떤 상황에서는 agent가 드론이고 어떤 상황에서는 agent가 트럭이고 이렇게 할 수 있나? 둘다 공존이 아니라, 하나 활성화 하나 비활성화 이렇게. 그런데 다른 시나리오를 생각하면, 둘다 있어야 할 것 같다. 아까 어떤 것 하나도 트럭과 중복되는게 있었던 것 같은데
     'IsDroneBack',
     'IsDropoffAssigned',
     'IsNomoredropoff'
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

class CalculateDropoffLocation(SyncAction):
    ''' 
    mTSP 알고리즘, K-means 등 plugin을 통해 dropoff 지점들을 계산한다.
    이후 첫번째로 이동할 dropoff location을 할당 받는다.
    calculate해서 dropoff_locations 리스트에 넣어야 할 듯
    '''
    def __init__(self, name, agent):
        super().__init__(name, self._calculate_location)

    def _calculate_location(self, agent, blackboard):
        agent.dropoff_location = agent.calculate_dropoff()
        return Status.SUCCESS

class IsDropoffAssigned(SyncAction): 
    '''
    dropoff location 잘 할당 받았는지 확인한다. (더블 check할 필요가 있는가)
    '''
    def __init__(self, name, agent):
        super().__init__(name, self._check)

    def _check(self, agent, blackboard):
        return Status.SUCCESS if agent.is_dropoff_assigned() else Status.FAILURE

class IsActivated(SyncAction):
    '''
    트럭이 Dropoff지점에 도착했는지 확인. 
    '''
    def __init__(self, name, agent):
        super().__init__(name, self._check)

    def _check(self, agent, blackboard):
        if agent.is_at_dropoff():
            return Status.SUCCESS
        else:
            return Status.FAILURE

class MoveToDropoff(SyncAction):
    '''
    위치가 dropoff location과 같으면 도착인데, dropoff location에게 가는 중에 "IsArrivedAtDropoff"노드가 함께 작동되며
    도착하지 않으면 계속 dropoff location으으로 트럭이 이동한다.
    '''
    def __init__(self, name, agent):
        super().__init__(name, self._move)

    def _move(self, agent, blackboard):
        if agent.move_to_dropoff(agent.dropofflocation):
            return Status.SUCCESS
        else:
            return Status.RUNNING

class ActivateDroneBT(SyncAction):
    '''
    트럭은 dropoff location에 도착을 했고 이제 트럭은 가만히 드론이 작업을 마치고 올 때까지 대기하며,
    드론은 이제 작업을 시작한다. 드론의 행동 logic은 drone_bt에 있다.
    '''
    def __init__(self, name, agent):
        super().__init__(name, self._activate)

    def _activate(self, agent, blackboard):
        agent.activate_drone()
        return Status.SUCCESS

class IsDroneBack(SyncAction):
    '''
    작업을 나간 드론은 트럭에 다시 복귀를 해야한다. 복귀를 하면 트럭은 다른 dropoff location으로 이동한다.
    드론이 작업을 나가서 트럭으로 다시 복귀할 때까지 트럭은 정지 상태로 대기한다. 
    드론의 위치와 dropoff location의 위치와 같으면, 드론은 트럭에 복귀했다고 판단할 수 있다. 
    '''
    def __init__(self, name, agent):
        super().__init__(name, self._check)

    def _check(self, agent, blackboard):
        if agent.is_at_truck():
            return Status.SUCCESS
        else:
            return Status.FAILURE
    
class WaitForDrone(SyncAction):
    '''
    위치가 dropoff location과 같으면 도착인데, dropoff location에에 가는 중에 "IsDroneBack"노드가 함께 작동되며
    도착하지 않으면 계속 dropoff location으로 드론이 이동한다.
    '''
    def __init__(self, name, agent):
        super().__init__(name, self._wait)

    def _wait(self, agent, blackboard):
        if agent.is_at_truck():
            return Status.SUCCESS
        else:
            return Status.RUNNING

class IsNomoredropoff(SyncAction):
    '''
    트럭은 담당구역의 모든 dropoff location을 돌며 작업을 모두 완수해야 depot으로 복귀할 수 있다.
    그러기 위해서 하나의 dropoff location이 끝나면 다른 작업은 또 없는지 확인해야 한다. 
    다른 작업은 없는지 확인하는 것이 이 노드이다.
    '''
    def __init__(self, name, agent):
        super().__init__(name, self._check)

    def _check(self, agent, blackboard):
        if agent.no_more_dropoff():
            return Status.SUCCESS
        else:
            return Status.FAILURE
        

class UpdateDropoffLocation(SyncAction):
    def __init__(self, name, agent):
        super().__init__(name, self._update_location)

    def _update_location(self, agent, blackboard):
        # 다음 dropoff 위치를 찾고 ID 할당
        agent.dropofflocation = agent.get_next_dropoff()
        
        # 만약 새로운 dropoff가 없다면 실패 반환 (Depot으로 이동하는 로직을 따르게 됨)
        if agent.dropofflocation is None:
            return Status.FAILURE

        # 🚀 ID도 설정
        agent.assigned_dropoff_location_id = id(agent.dropofflocation)

        return Status.FAILURE  # 트리를 다시 실행하게 하기 위함



class MoveToDepot(SyncAction):
    '''
    "IsNomoredropoff" 노드를 통해 트럭이 더 이상 할당할 dropoff location이 없다면, depot으로 복귀를 하게된다.
    따라서, "IsNomoredropoff" 노드에서 더 이상 작업이 없다면 이 노드가 실행되어 트럭은 depot으로 이동한다. 
    이 노드는 "IsArrivedAtDepot"노드를 계속 확인하며 "IsArrivedAtDepot"노드가 success할 때까지 트럭은 depot으로 다가간다.
    '''
    def __init__(self, name, agent):
        super().__init__(name, self._move)

    def _move(self, agent, blackboard):
        if agent.move_to_depot(agent.depot_position):
            return Status.SUCCESS  
        else:
            return Status.RUNNING
    
class IsArrivedAtDepot(SyncAction):
    '''
    트럭이 depot으로 움직일 때 "MoveToDepot"노드와 함께 작동하며, 트럭의 위치와 모든 드론의 위치가 depot과 같으면 success를 반환한다. 
    '''
    def __init__(self, name, agent):
        super().__init__(name, self._check)

    def _check(self, agent, blackboard):
        if agent.is_at_depot():
            return Status.SUCCESS 
        else:
            return Status.FAILURE

class Takeoff(SyncAction):
    '''
    "IsActivated"노드를 통해 드론을 적재한 트럭이 dropoff location에 도착했다면, 이제 드론을 작업 시켜야 하기 때문에 트럭 노드에서 plugin을 통해 task의 정보를 받았든
    이 노드에서 plugin을 통해 task의 정보를 받든 해서 드론을 task에게 보낸다. 
    '''
    def __init__(self, name, agent):
        super().__init__(name, self._deploy)

    def _deploy(self, agent, blackboard):
        agent.activate_drone()
        return Status.SUCCESS

class IsArrivedAtTaskLocation(SyncAction):
    '''
    drone의 위치가 task의 위치와 같으면 도착했다고 본다.
    '''
    def __init__(self, name, agent):
        super().__init__(name, self._check)

    def _check(self, agent, blackboard):
        if agent.is_at_task_location():
            return Status.SUCCESS  
        else:
            return Status.FAILURE

class MoveToTaskLocation(SyncAction):
    '''
    드론이 task로 움직일 때 "IsArrivedAtTaskLocation"노드와 함께 작동하며, 드론의 위치가 task와와 같으면 success를 반환한다.
    '''
    def __init__(self, name, agent):
        super().__init__(name, self._move)

    def _move(self, agent, blackboard):
        if agent.move_to_task(agent.task_location):
            return Status.SUCCESS
        else:
            return Status.RUNNING

class DropItem(SyncAction):
    '''
    물건을 배송한다. 이곳에는 나중에 추가로 이미지를 구현하여, 상자를 놓고 몇 초뒤에 사라지게 할 수 있겠디. 근데 우선은 task가 사라지게끔 하는 걸로
    '''
    def __init__(self, name, agent):
        super().__init__(name, self._drop)

    def _drop(self, agent, blackboard):
        agent.drop_item()
        return Status.SUCCESS

class IsTruckAssigned(SyncAction):
    '''
    드론이 복귀할 트럭의 정보를 재차 확인한다. 
    '''
    def __init__(self, name, agent):
        super().__init__(name, self._check)

    def _check(self, agent, blackboard):
        if agent.is_truck_assigned():
            return Status.SUCCESS
        else:
            return Status.FAILURE

class AssignTruck(SyncAction):
    '''
    드론이 특정 트럭으로 복귀해야 할 때, 해당 트럭을 할당하는 노드.
    기존 트럭으로 돌아가는 것이 기본이지만, 상황에 따라 다른 트럭으로 변경될 가능성을 고려하여 확장성을 추가함.
    
    - 드론이 처음 배정된 트럭이 근처에 있을 경우, 기존 트럭 ID를 유지.
    - 만약 기존 트럭이 없거나 새로운 트럭이 더 적절하다면, 새 트럭을 탐색 후 할당.
    
    성공적으로 트럭이 할당되면 SUCCESS 반환.
    트럭이 할당되지 않으면 FAILURE 반환 (이후 fallback 처리 필요)
    '''
    def __init__(self, name, agent):
        super().__init__(name, self._assign_truck)

    def _assign_truck(self, agent, blackboard):
        nearest_truck = agent.find_nearest_truck()
        
        if nearest_truck:
            agent.assigned_truck_id = nearest_truck.agent_id  # 트럭 ID 저장
            agent.truck_location = nearest_truck.position  # 트럭 위치 업데이트
            return Status.SUCCESS
        '''
        truck_location, assigned_truck_id 등 구현 해야함.
        '''
        
        return Status.FAILURE  # 트럭 할당 실패 시 Fallback이 실행됨
    
class IsArrivedAtTruck(SyncAction):
    
    '''
    모든 task의 작업을 마치면 트럭으로 복귀를 하게되는데, 그때 드론이 트럭으로 복귀를 했는가 확인하는 노드이다. 이는 "MoveToTruck"노드와 함께 작동하며
    이 노드가 failure이면 "MoveToTruck"노드가 작동된다. 
    '''
    def __init__(self, name, agent):
        super().__init__(name, self._check)

    def _check(self, agent, blackboard):
        if agent.is_at_truck():
            return Status.SUCCESS
        else:
            return Status.FAILURE
    
class MoveToTruck(SyncAction):
    '''
    드론은 모든 task의 작업을 마치면 트럭으로 복귀한다. 이때, "IsArrivedAtTruck"를 계속 확인하여, failure이면 드론을 트럭으로 계속 이동 시킨다. 
    '''
    def __init__(self, name, agent):
        super().__init__(name, self._move)

    def _move(self, agent, blackboard):
        if agent.move_to_target(agent.truck_location):
            return Status.SUCCESS  
        else:
            return Status.RUNNING

class DockToTruck(SyncAction):
    '''
    드론의 위치가 dropoff에 있는 트럭의 위치와 같다면 드론은 트럭에 적재된다. 
    '''
    def __init__(self, name, agent):
        super().__init__(name, self._dock)

    def _dock(self, agent, blackboard):
        if agent.dock_to_truck():
            return Status.SUCCESS  
        else:
            return Status.RUNNING