import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from collections import defaultdict
import os
os.environ["OMP_NUM_THREADS"] = "1"

# 데이터 생성
num_samples = 40  # 고객 수
max_customers_per_cluster = 3  # 클러스터당 고객 최대 수
x_min, x_max = -10, 10
y_min, y_max = -10, 10

X = np.column_stack((np.random.uniform(x_min, x_max, num_samples),
                     np.random.uniform(y_min, y_max, num_samples)))

# 초기 클러스터 개수 설정
num_initial_clusters = num_samples // max_customers_per_cluster
if num_samples % max_customers_per_cluster != 0:
    num_initial_clusters += 1

# K-means 클러스터링 수행
kmeans = KMeans(n_clusters=num_initial_clusters, init='k-means++', n_init='auto', max_iter=100, random_state=None)
labels = kmeans.fit_predict(X)

# 클러스터링 결과 정리
cluster_dict = defaultdict(list)
for i, label in enumerate(labels):
    cluster_dict[label].append(X[i])

adjusted_clusters = []
for cluster_data in cluster_dict.values():
    cluster_data = np.array(cluster_data)
    while len(cluster_data) > max_customers_per_cluster:
        split_kmeans = KMeans(n_clusters=2, init='k-means++', n_init='auto', max_iter=100, random_state=None)
        split_labels = split_kmeans.fit_predict(cluster_data)
        
        cluster1 = cluster_data[split_labels == 0]
        cluster2 = cluster_data[split_labels == 1]
        
        if len(cluster1) > max_customers_per_cluster:
            adjusted_clusters.append(cluster1[:max_customers_per_cluster])
            cluster_data = np.vstack((cluster1[max_customers_per_cluster:], cluster2))
        elif len(cluster2) > max_customers_per_cluster:
            adjusted_clusters.append(cluster2[:max_customers_per_cluster])
            cluster_data = np.vstack((cluster1, cluster2[max_customers_per_cluster:]))
        else:
            adjusted_clusters.append(cluster1)
            cluster_data = cluster2

    if len(cluster_data) > 0:
        adjusted_clusters.append(cluster_data)

# 클러스터 중심 계산
if len(adjusted_clusters) == 0:
    raise ValueError("No valid clusters generated!")

final_initial_centers = np.array([cluster.mean(axis=0) for cluster in adjusted_clusters if len(cluster) > 0])

if final_initial_centers.shape[0] == 0:
    raise ValueError("No valid cluster centers found!")

truck_start = np.array([[0, 0]])
locations = np.vstack((truck_start, final_initial_centers))

# 📌 Nearest Neighbor 알고리즘 적용
def nearest_neighbor_tsp(locations):
    num_nodes = len(locations)
    unvisited = set(range(1, num_nodes))  # 출발지(0번)는 제외
    path = [0]  # 트럭 출발지에서 시작

    while unvisited:
        last_visited = path[-1]
        nearest = min(unvisited, key=lambda x: np.linalg.norm(locations[last_visited] - locations[x]))
        path.append(nearest)
        unvisited.remove(nearest)

    path.append(0)  # 마지막에 다시 출발지로 복귀
    return path

# 📌 2-opt 최적화 함수
def two_opt(path, locations, max_iterations=100):
    def compute_distance(path):
        return sum(np.linalg.norm(locations[path[i]] - locations[path[i + 1]]) for i in range(len(path) - 1))

    best_path = path
    best_distance = compute_distance(best_path)
    improved = True
    iteration = 0

    while improved and iteration < max_iterations:
        improved = False
        for i in range(1, len(path) - 2):  # 출발지(0) 제외
            for j in range(i + 1, len(path) - 1):
                new_path = best_path[:i] + best_path[i:j+1][::-1] + best_path[j+1:]
                new_distance = compute_distance(new_path)

                if new_distance < best_distance:
                    best_path = new_path
                    best_distance = new_distance
                    improved = True
        iteration += 1

    return best_path

# Nearest Neighbor 경로 생성
nn_path = nearest_neighbor_tsp(locations)
# 2-opt 적용하여 경로 최적화
optimized_path = two_opt(nn_path, locations)

# 📌 시각화
plt.figure(figsize=(10, 6))

# 클러스터 플롯
for idx, cluster in enumerate(adjusted_clusters):
    if len(cluster) > 0:
        plt.scatter(cluster[:, 0], cluster[:, 1], s=100)

# 클러스터 중심과 트럭 출발지 표시
plt.scatter(final_initial_centers[:, 0], final_initial_centers[:, 1], c='red', marker='X', s=200, label='Cluster Centers')
plt.scatter(truck_start[:, 0], truck_start[:, 1], c='blue', marker='s', s=300, label='Truck Start')

# 최적 경로 시각화
for i in range(len(optimized_path) - 1):
    start, end = optimized_path[i], optimized_path[i + 1]
    plt.plot([locations[start, 0], locations[end, 0]], [locations[start, 1], locations[end, 1]], 'k--', linewidth=1.5)

plt.title(f"Optimized Truck Route (Nearest Neighbor + 2-opt)")
plt.legend()
plt.xlim(x_min, x_max)
plt.ylim(y_min, y_max)
plt.grid(True)
plt.show()