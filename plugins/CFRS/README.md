# CFRS
<작업 수 40개, 트럭 수 1개, 클러스터링 당 작업 포함 최대 개수 10개>
* 클러스터링(K-means)로 고객을 그룹화 → 각 그룹 중심을 구함 → 트럭의 최적 이동 경로(TSP) 계산
* 고객이 많을 경우 K-means를 반복적으로 수행하여 클러스터 크기를 조정.
* 트럭의 이동 경로는 Brute-force 방식을 사용하여 최적화(규모가 크면 다른 방법 필요).
![Figure_1](https://github.com/user-attachments/assets/e2fb590e-e46c-448a-8d83-07d5b865752e)
