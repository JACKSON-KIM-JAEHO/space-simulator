# SPACE (Swarm Planning And Control Evaluation) Simulator


**SPACE** Simulator is a pygame-based application for simulating decentralized agent behavior using behavior trees. 
By integrating your custom decision-making algorithms as plugins, SPACE enables rigorous testing and comparative analysis against pre-existing algorithms. 

The official documentation of the SPACE simulator is available at [http://space-simulator.rtfd.io/](http://space-simulator.rtfd.io/). 


<div style="display: flex; flex-direction: row;">
    <img src="output/2024-07-13/RandomAssignment_100_agents_300_tasks_2024-07-13_00-41-18.gif" alt="GIF" width="400" height="300">
    <img src="output/2024-07-13/RandomAssignment_1000_agents_3000_tasks_2024-07-13_00-38-13.gif" alt="GIF" width="400" height="300">
</div>

- Example: (Left) `num_agents = 100`, `num_tasks = 300`; (Right) `num_agents = 1000`, `num_tasks = 3000`

<div style="display: flex; flex-direction: row;">
    <img src="output/2024-07-27/GRAPE_30_agents_200_tasks_2024-07-27_01-35-35.gif" alt="GIF" width="400" height="300">
    <img src="output/2024-07-27/CBBA_30_agents_200_tasks_2024-07-27_01-34-05.gif" alt="GIF" width="400" height="300">
</div>

- Example: (Left) `GRAPE`; (Right) `CBBA`; (Common) `num_agents = 30`, `num_tasks = 200 (static); 50 x 3 times (dynamic)`


## Features

- Simulates multiple agents performing tasks
- Agents use behavior trees for decision-making
- Real-time task assignment and execution
- Debug mode for visualizing agent behavior



## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/inmo-jang/space-simulator.git
    cd space-simulator
    ```

2. Install the required dependencies:
    ```sh
    pip install -r requirements.txt
    ```

3. Run the simulator:
    ```sh
    python main.py
    ```


## Configuration

Modify the `config.yaml` file to adjust simulation parameters:
- Number of agents and tasks
- Screen dimensions
- Agent behavior parameters

Refer to the configuration guide [CONFIG_GUIDE.md](/docs/CONFIG_GUIDE.md)



## Usage

### Controls
- `ESC` or `Q`: Quit the simulation
- `P`: Pause/unpause the simulation
- `S`: Start/stop recording the simulation as a GIF file
- `R`: Reset the simulation

### Monte Carlo Analysis

1. Set `mc_runner.yaml` for your purpose and run the following:
    ```sh
    python mc_runner.py
    ``` 

2. Set `mc_comparison.yaml` and run the following:
    ```sh
    python mc_analyzer.py
    ``` 



## Code Structure
- `main.py`: Entry point of the simulation, initializes pygame and manages the main game loop.
- `/modules/`
    - `agent.py`: Defines the Agent class and manages agent behavior.
    - `task.py`: Defines the Task class and manages task behavior.
    - `behavior_tree.py`: Implements behavior tree nodes and execution logic.
    - `utils.py`: Utility functions and configuration loading.
- `/plugins/`
    - `my_decision_making_plugin.py`: Template for decision-making algorithms for each agent.


## Contributing
Feel free to fork the repository and submit pull requests. 
Refer to [TODO.md](/docs/TODO.md) for a list of pending tasks and upcoming features.

## Citations
Please cite this work in your papers!
- [Inmo Jang, *"SPACE: A Python-based Simulator for Evaluating Decentralized Multi-Robot Task Allocation Algorithms"*, arXiv:2409.04230 [cs.RO], 2024](https://arxiv.org/abs/2409.04230)


## License
[GNU GPLv3](LICENSE)


## Test Results by Scenario

| Scenario         | Status |
| ---------------- | ------ |
| Simple           | ![Simple scenario test](https://github.com/inmo-jang/space-simulator/actions/workflows/main_simple.yaml/badge.svg) |
| Harbor Logistics | ![Harbor Logistics scenario test](https://github.com/inmo-jang/space-simulator/actions/workflows/main_harbor_logistics.yaml/badge.svg) |
| Drone Delivery   | ![Drone Delivery scenario test](https://github.com/inmo-jang/space-simulator/actions/workflows/main_drone_delivery.yaml/badge.svg) |
