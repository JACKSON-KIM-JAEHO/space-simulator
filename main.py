import pygame
import asyncio
import argparse
import cProfile

from modules.utils import pre_render_text, save_gif, set_config

# Parse command line arguments
parser = argparse.ArgumentParser(description='SPADE (Swarm Planning And Decision Evalution) Simulator')
parser.add_argument('--config', type=str, default='config.yaml', help='Path to the configuration file (default: --config=config.yaml)')
args = parser.parse_args()

# Load configuration
set_config(args.config)
from modules.utils import config  # Import the global config after setting it

sampling_freq = config['simulation']['sampling_freq']
sampling_time = 1.0 / sampling_freq  # in seconds
screen_height = config['simulation']['screen_height']
screen_width = config['simulation']['screen_width']
debug_mode = config['simulation']['debug_mode']
gif_recording_fps = config['simulation']['gif_recording_fps']
profiling_mode = config['simulation']['profiling_mode']
rendering_mode = config.get('simulation').get('rendering_mode', "Screen")
rendering_options = config.get('simulation').get('rendering_options', {})

# Initialize pygame
pygame.init()
if rendering_mode == "Screen":
    screen = pygame.display.set_mode((screen_width, screen_height), pygame.RESIZABLE)
else:
    screen = None  # No screen initialization if rendering is disabled

# screen = pygame.display.set_mode((screen_width, screen_height), pygame.RESIZABLE)
background_color = (173, 255, 47)

# Set logo and title
logo_image_path = 'assets/logo.jpg'  # Change to the path of your logo image
logo = pygame.image.load(logo_image_path)
pygame.display.set_icon(logo)
pygame.display.set_caption('SPADE(Swarm Planning And Decision Evaluation) Simulator')  # Change to your desired game title

# Initialize tasks
from modules.task import generate_tasks
tasks = generate_tasks()

# Initialize agents with behavior trees, giving them the information of current tasks
from modules.agent import generate_agents
agents = generate_agents(tasks)

# Pre-rendered text for performance improvement
mission_completed_text = pre_render_text("MISSION COMPLETED", 72, (0, 0, 0))



# Main game loop
async def game_loop():
    running = True
    clock = pygame.time.Clock()
    game_paused = False
    mission_completed = False

    # Recording variables
    recording = False
    frames = []    

    # Initialize simulation time
    simulation_time = 0.0
    last_print_time = 0.0   # Variable to track the last time tasks_left was printed

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                    running = False
                elif event.key == pygame.K_p:
                    game_paused = not game_paused
                elif event.key == pygame.K_r:
                    if not recording:
                        recording = True
                        frames = [] # Clear any existing frames
                        last_frame_time = simulation_time
                        print("Recording started...") 
                    else:
                        recording = False
                        print("Recording stopped.")
                        save_gif(frames)            

        if not game_paused and not mission_completed:
            # Run behavior trees for each agent without rendering
            for agent in agents:
                await agent.run_tree()    
                agent.local_broadcast(agents)
                agent.update()

            # Status retrieval
            simulation_time += sampling_time
            tasks_left = sum(1 for task in tasks if not task.completed)
            if tasks_left == 0:
                mission_completed = True            

            # Rendering
            if rendering_mode == "Screen":
                screen.fill(background_color)

                # Draw tasks with task_id displayed
                for task in tasks:
                    task.draw(screen)
                    if rendering_options.get('task_id'): # Draw each task's ID
                        task.draw_task_id(screen)

                # Draw agents network topology
                if rendering_options.get('agent_communication_topology'):
                    for agent in agents:
                        agent.draw_communication_topology(screen, agents)

                # Draw agents
                for agent in agents:
                    agent.draw(screen)
                    if rendering_options.get('agent_tail'): # Draw each agent's trajectory tail
                        agent.draw_tail(screen)
                    if rendering_options.get('agent_id'): # Draw each agent's ID
                        agent.draw_agent_id(screen)
                    if rendering_options.get('agent_assigned_task_id'): # Draw each agent's assigned task ID
                        agent.draw_assigned_task_id(screen)
                    

                # Display task quantity and elapsed simulation time                
                task_time_text = pre_render_text(f'Tasks left: {tasks_left} Time: {simulation_time:.2f}s', 36, (0, 0, 0))
                screen.blit(task_time_text, (screen_width - 300, 20))
                if 'evolution_number' in agent.message_to_share: # For GRAPE
                    partition_evolution_number = agent.message_to_share['evolution_number']
                    partition_evolution_number_text = pre_render_text(f'Partition evolution number: {partition_evolution_number}', 36, (0, 0, 0))
                    screen.blit(partition_evolution_number_text, (20, 20))

                # Check if all tasks are completed
                if mission_completed:
                    text_rect = mission_completed_text.get_rect(center=(screen_width // 2, screen_height // 2))
                    screen.blit(mission_completed_text, text_rect)


                pygame.display.flip()
                clock.tick(sampling_freq)

                # Capture frame for recording
                if recording:
                    if simulation_time - last_frame_time > 1.0/gif_recording_fps: # Capture frame if 0.5 seconds elapsed
                        frame = pygame.surfarray.array3d(screen)
                        frames.append(frame)            
                        last_frame_time = simulation_time                

            elif rendering_mode == "Terminal": # if rendering_mode is False
                if simulation_time - last_print_time > 0.5:
                    print(f'Tasks left: {tasks_left} Time: {simulation_time:.2f}s')
                    last_print_time = simulation_time
                if mission_completed:
                    print(f'Tasks left: {tasks_left} Time: {simulation_time:.2f}s')
                    print(f'MISSION COMPLETED')
                    running = False
            else:
                if mission_completed:
                    print(f'MISSION COMPLETED with Time: {simulation_time:.2f}s')
                    running = False



    pygame.quit()

def main():
    asyncio.run(game_loop())

# Run the game
if __name__ == "__main__":    
    if profiling_mode:
        cProfile.run('main()', sort='cumulative')
    else:
        main()