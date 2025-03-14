import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from scipy.spatial.distance import euclidean
from itertools import permutations

# 파라미터 설정
num_jobs = 20  # 작업 개수
num_drones = 4  # 드론 개수 (클러스터 개수)
num_trucks = 1  # 트럭 개수 (TSP 수행)
np.random.seed(42)

# 랜덤 작업 좌표 생성
jobs = np.random.rand(num_jobs, 2) * 100

# K-Means 클러스터링 수행
kmeans = KMeans(n_clusters=num_drones, random_state=42, n_init=10)
kmeans.fit(jobs)
labels = kmeans.labels_
centroids = kmeans.cluster_centers_

# TSP (Traveling Salesman Problem) 해결: 브루트포스 방식
def tsp_bruteforce(points):
    min_path = None
    min_distance = float('inf')
    
    for perm in permutations(range(len(points))):
        dist = sum(euclidean(points[perm[i]], points[perm[i+1]]) for i in range(len(points)-1))
        if dist < min_distance:
            min_distance = dist
            min_path = perm
    
    return min_path, min_distance

# 클러스터 중심을 기반으로 TSP 해결
tsp_path, tsp_distance = tsp_bruteforce(centroids)

# 시각화
plt.figure(figsize=(10, 6))

# 작업 및 클러스터 시각화
for i in range(num_drones):
    cluster_jobs = jobs[labels == i]
    plt.scatter(cluster_jobs[:, 0], cluster_jobs[:, 1], label=f'Cluster {i+1}')
    plt.scatter(centroids[i, 0], centroids[i, 1], color='red', marker='x', s=200)

# TSP 경로 시각화
for i in range(len(tsp_path) - 1):
    plt.plot([centroids[tsp_path[i], 0], centroids[tsp_path[i+1], 0]],
             [centroids[tsp_path[i], 1], centroids[tsp_path[i+1], 1]],
             'k--', linewidth=2)

plt.xlabel('X Coordinate')
plt.ylabel('Y Coordinate')
plt.title('CFRS Clustering & TSP Solution')
plt.legend()
plt.show()
