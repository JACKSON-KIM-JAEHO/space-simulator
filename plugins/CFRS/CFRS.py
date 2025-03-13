'''
이 파일을 통해 agent 작업 할당이 이루어짐.
이곳에서 작업 할당이 된 것을 바탕으로 다른 파일에서 정보를 가져다 사용함.

+ mSTP 알고리즘 중 클러스터링 기반 접근법인 CFRS (Cluster-First, Route-Second)
+ 다른 코드 파일들과 연동될 수 있게 변수명 잘 고려하기
'''



import random
import copy
from modules.utils import config
from scipy.spatial.distance import euclidean
from itertools import permutations

# 설정값 불러오기
NUM_SALESPEOPLE = config['decision_making']['CFRS'].get('num_salespeople', 3)
MAX_ITERATIONS = config['decision_making']['CFRS'].get('max_iterations', 100)

def solve_mTSP(task_positions, num_agents):
    """
    여러 에이전트(mTSP: Multiple Traveling Salesman Problem) 경로를 생성
    :param task_positions: 태스크 위치 리스트 [(x, y), ...]
    :param num_agents: 에이전트 수
    :return: 에이전트별 최적 경로 리스트
    """
    if not task_positions or num_agents == 0:
        return []

    # k-means 기반으로 클러스터링 (에이전트 수만큼)
    cluster_centers = random.sample(task_positions, min(num_agents, len(task_positions)))
    clusters = {i: [] for i in range(len(cluster_centers))}

    for _ in range(MAX_ITERATIONS):
        clusters = {i: [] for i in range(len(cluster_centers))}
        for task in task_positions:
            distances = [euclidean(task, center) for center in cluster_centers]
            assigned_cluster = distances.index(min(distances))
            clusters[assigned_cluster].append(task)

        new_centers = [tuple(map(lambda x: sum(x) / len(x), zip(*clusters[i])))
                       if clusters[i] else cluster_centers[i] for i in range(len(cluster_centers))]

        if new_centers == cluster_centers:
            break  # 클러스터링 수렴
        cluster_centers = new_centers

    # 각 클러스터에 대해 최적 경로 찾기
    routes = []
    for cluster_tasks in clusters.values():
        if len(cluster_tasks) <= 1:
            routes.append(cluster_tasks)
            continue

        best_route = min(permutations(cluster_tasks), key=lambda perm: sum(euclidean(perm[i], perm[i+1]) for i in range(len(perm)-1)))
        routes.append(best_route)

    return routes

class CFRS:
    def __init__(self, agent):
        self.agent = agent        
        self.assigned_task = None
        self.satisfied = False  # 의사결정 완료 여부
        self.clusters = {}  # 태스크 클러스터 리스트
        self.routes = {}  # 클러스터별 최적 경로
        self.task_assignments = {}
        self.assigned_route = []
        
    def decide(self, blackboard):
        """
        Output:
            - `task_id`, if task allocation works well
            - `None`, otherwise
        """
        # 블랙보드에서 정보 가져오기
        local_tasks_info = blackboard.get('local_tasks_info', [])
        local_agents_info = blackboard.get('local_agents_info', [])

        # 주변에 태스크가 없다면 결정 프로세스 종료
        if not local_tasks_info:
            return None
        
        # 이전 태스크가 완료되었는지 확인
        if self.assigned_task is not None and self.assigned_task.completed:
            self.assigned_task = None
            self.satisfied = False
        
        # 지역적 의사결정 수행 (클러스터링 및 라우팅)
        if not self.satisfied:
            self.initialize_clustering(local_tasks_info)
            self.routes = solve_mTSP([task.position for task in local_tasks_info], NUM_SALESPEOPLE)
            self.assign_tasks()
            
            # 공유할 메시지 생성
            self.agent.message_to_share = {
                "clusters": self.clusters,
                "routes": self.routes
            }
            
            self.satisfied = True
        
        return self.decide_next_task()
    
    def initialize_clustering(self, local_tasks_info):
        """
        Cluster-First 단계: k-means 기반 태스크 클러스터링 수행
        """
        tasks = [task.position for task in local_tasks_info if not task.completed]
        num_tasks = len(tasks)

        if num_tasks == 0:
            return

        # k-means 방식으로 클러스터링 진행
        cluster_centers = random.sample(tasks, min(NUM_SALESPEOPLE, num_tasks))
        clusters = {i: [] for i in range(len(cluster_centers))}
        
        for _ in range(MAX_ITERATIONS):
            clusters = {i: [] for i in range(len(cluster_centers))}
            
            for task in tasks:
                distances = [euclidean(task, center) for center in cluster_centers]
                assigned_cluster = distances.index(min(distances))
                clusters[assigned_cluster].append(task)
            
            new_centers = [tuple(map(lambda x: sum(x)/len(x), zip(*clusters[i]))) if clusters[i] else cluster_centers[i] for i in range(len(cluster_centers))]
            
            if new_centers == cluster_centers:
                break
            cluster_centers = new_centers
        
        self.clusters = clusters

    def assign_tasks(self):
        """
        각 에이전트에게 최적 경로를 기반으로 태스크 할당
        """
        self.task_assignments = {self.agent.agent_id: [] for _ in range(NUM_SALESPEOPLE)}
        
        for cluster_id, route in enumerate(self.routes):
            agent_id = cluster_id % NUM_SALESPEOPLE  # 순환 할당 방식
            self.task_assignments[agent_id].extend(route)
        
        self.assigned_route = self.task_assignments.get(self.agent.agent_id, [])
    
    def decide_next_task(self):
        """
        현재 할당된 경로에서 다음 태스크 반환
        """
        if not self.assigned_route:
            return None
        
        self.assigned_task = self.assigned_route.pop(0)
        return self.assigned_task.task_id if self.assigned_task else None
