import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from collections import defaultdict
from itertools import permutations

# make data (random position)
num_samples = 10  # number of package (customer)
num_trucks = 1  # number of truck
max_customers_per_cluster = 2  # Adjust this to test different cases

x_min, x_max = -10, 10
y_min, y_max = -10, 10

X = np.column_stack((
    np.random.uniform(x_min, x_max, num_samples),
    np.random.uniform(y_min, y_max, num_samples)
))

# number of clusters
'''
클러스터 개수 정의
'''
num_initial_clusters = num_samples // max_customers_per_cluster
if num_samples % max_customers_per_cluster != 0:
    num_initial_clusters += 1   

# Perform 1st K-means clustering
max_iter_kmeans = 100 #k-means 알고리즘의 반복 횟수
initial_kmeans = KMeans(n_clusters=num_initial_clusters, init='k-means++', n_init='auto', max_iter=max_iter_kmeans, random_state=None)
initial_labels = initial_kmeans.fit_predict(X)

cluster_dict = defaultdict(list)
for i, label in enumerate(initial_labels):
    cluster_dict[label].append(X[i])

adjusted_clusters = []
for cluster_data in cluster_dict.values():
    cluster_data = np.array(cluster_data)

    while len(cluster_data) > max_customers_per_cluster:
        split_kmeans = KMeans(n_clusters=2, init='k-means++', n_init='auto', max_iter=max_iter_kmeans, random_state=None)
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

    if len(cluster_data) > 0:  # 빈 클러스터는 추가하지 않음
        adjusted_clusters.append(cluster_data)

# Ensure we have valid clusters before computing centers
if len(adjusted_clusters) == 0:
    print("Error: No valid clusters generated!")
    exit()

# Cluster centers and the truck's starting position (0,0)
final_initial_centers = np.array([cluster.mean(axis=0) for cluster in adjusted_clusters if len(cluster) > 0])

if final_initial_centers.shape[0] == 0:
    print("Error: No valid cluster centers found!")
    exit()

truck_start = np.array([[0, 0]])
locations = np.vstack((truck_start, final_initial_centers))

# TSP using brute-force approach
n = len(locations)
best_path = None
best_distance = float("inf")

for perm in permutations(range(1, n)):  # Start from 1 (excluding truck start)
    path = [0] + list(perm) + [0]
    distance = sum(np.linalg.norm(locations[path[i]] - locations[path[i + 1]]) for i in range(len(path) - 1))

    if distance < best_distance:
        best_distance = distance
        best_path = path

# Visualization
plt.figure(figsize=(10, 6))  # Adjust size to prevent large plots

# Plot clusters
for idx, cluster in enumerate(adjusted_clusters):
    if len(cluster) > 0:  # Avoid empty clusters
        plt.scatter(cluster[:, 0], cluster[:, 1], s=100, label=f'Cluster {idx}')

# Plot adjusted centers and truck start
plt.scatter(final_initial_centers[:, 0], final_initial_centers[:, 1], c='red', marker='X', s=200, label='Adjusted Centers')
plt.scatter(truck_start[:, 0], truck_start[:, 1], c='blue', marker='s', s=300, label='Truck Start')

# Draw TSP path
for i in range(len(best_path) - 1):
    start, end = best_path[i], best_path[i + 1]
    plt.plot([locations[start, 0], locations[end, 0]], [locations[start, 1], locations[end, 1]], 'k--', linewidth=1.5)

plt.title(f"Customer Clustering and Truck Route (TSP)")
plt.legend()
plt.xlim(x_min, x_max)
plt.ylim(y_min, y_max)
plt.grid(True)
plt.show()