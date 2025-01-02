import pygame
import importlib
from modules.utils import pre_render_text, ResultSaver
from scenarios.simple.task import generate_tasks
from scenarios.simple.agent import generate_agents

class Env:
    def __init__(self, config):
        self.config = config
        self.sampling_freq = config['simulation']['sampling_freq']
        self.sampling_time = 1.0 / self.sampling_freq  # in seconds
        self.max_simulation_time = config['simulation'].get('max_simulation_time', 0)
        self.screen_height = config['simulation']['screen_height']
        self.screen_width = config['simulation']['screen_width']
        self.gif_recording_fps = config['simulation']['gif_recording_fps']
        self.rendering_mode = config['simulation'].get('rendering_mode', "Screen")
        self.speed_up_factor = config.get('simulation').get('speed_up_factor', 1)
        self.rendering_options = config['simulation'].get('rendering_options', {})        


        self.save_gif = config.get('simulation').get('saving_options').get('save_gif', False)
        self.save_timewise_result_csv = config.get('simulation').get('saving_options').get('save_timewise_result_csv', False)
        self.save_agentwise_result_csv = config.get('simulation').get('saving_options').get('save_agentwise_result_csv', False)
        self.save_config_yaml = config.get('simulation').get('saving_options').get('save_config_yaml', False)


        # Dynamically import the decision-making module
        # self.decision_making_module_path = config['decision_making']['plugin']
        # module_path, _ = self.decision_making_module_path.rsplit('.', 1)
        # self.decision_making_module = importlib.import_module(module_path)

        
        # Initialize rendering
        pygame.init()        
        if self.rendering_mode == "Screen":
            self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.RESIZABLE)
            
            self.background_color = (224, 224, 224)

            # Set logo and title
            logo_image_path = 'assets/logo.jpg'  # Change to the path of your logo image
            logo = pygame.image.load(logo_image_path)
            pygame.display.set_icon(logo)
            pygame.display.set_caption('SPACE(Swarm Planning And Control Evaluation) Simulator')  # Change to your desired game title

        else:
            self.screen = None

        # Initialize agents and tasks
        self.tasks = generate_tasks()
        self.agents = generate_agents(self.tasks)

        # Pre-rendered text
        self.mission_completed_text = pre_render_text("MISSION COMPLETED", 72, (0, 0, 0))

        # Dynamic task generation variables
        self.dynamic_task_generation = config['tasks'].get('dynamic_task_generation', {})
        self.generation_enabled = self.dynamic_task_generation.get('enabled', False)
        self.generation_interval = self.dynamic_task_generation.get('interval_seconds', 10)
        self.max_generations = self.dynamic_task_generation.get('max_generations', 5)
        self.tasks_per_generation = self.dynamic_task_generation.get('tasks_per_generation', 5)
        
        

        # Initialize data recording
        self.data_records = []
        self.result_saver = ResultSaver(config)

        # Initialization        
        self.running = True
        self.clock = pygame.time.Clock()
        self.game_paused = False
        self.mission_completed = False        

        # Initialize simulation time           
        self.simulation_time = 0.0
        self.last_print_time = 0.0   # Variable to track the last time tasks_left was printed

        # Initialize dynamic task generation time
        self.generation_count = 0
        self.last_generation_time = 0.0     

        # Recording variables
        self.recording = False
        self.frames = []    
        if self.save_gif and self.rendering_mode == "Screen":
            self.recording = True
            self.frames = [] # Clear any existing frames
            self.last_frame_time = self.simulation_time
            print("Recording started...") 



    async def step(self):
        # Main simulation loop logic
        for agent in self.agents:
            await agent.run_tree()
            agent.update()

        # Status retrieval
        self.simulation_time += self.sampling_time
        self.tasks_left = sum(1 for task in self.tasks if not task.completed)
        if self.tasks_left == 0:
            self.mission_completed = not self.generation_enabled or self.generation_count == self.max_generations

        # Dynamic task generation
        if self.generation_enabled:
            self.generate_tasks_if_needed()


        # Stop if maximum simulation time reached
        if self.max_simulation_time > 0 and self.simulation_time > self.max_simulation_time:
            self.running = False

    def render(self):
        if self.rendering_mode == "Screen" and self.screen:
            self.screen.fill(self.background_color)
            
            # Draw agents network topology
            if self.rendering_options.get('agent_communication_topology'):
                for agent in self.agents:
                    agent.draw_communication_topology(self.screen, self.agents)

            # Draw agents
            for agent in self.agents:                    
                if self.rendering_options.get('agent_path_to_assigned_tasks'): # Draw each agent's path to its assigned tasks
                    agent.draw_path_to_assigned_tasks(self.screen)                    
                if self.rendering_options.get('agent_tail'): # Draw each agent's trajectory tail
                    agent.draw_tail(self.screen)
                if self.rendering_options.get('agent_id'): # Draw each agent's ID
                    agent.draw_agent_id(self.screen)
                if self.rendering_options.get('agent_assigned_task_id'): # Draw each agent's assigned task ID
                    agent.draw_assigned_task_id(self.screen)
                if self.rendering_options.get('agent_work_done'): # Draw each agent's assigned task ID
                    agent.draw_work_done(self.screen)
                if self.rendering_options.get('agent_situation_awareness_circle'): # Draw each agent's situation awareness radius circle    
                    agent.draw_situation_awareness_circle(self.screen)
                agent.draw(self.screen)

            # Draw tasks with task_id displayed
            for task in self.tasks:
                task.draw(self.screen)
                if self.rendering_options.get('task_id'): # Draw each task's ID
                    task.draw_task_id(self.screen)

            # Display task quantity and elapsed simulation time                
            task_time_text = pre_render_text(f'Tasks left: {self.tasks_left}; Time: {self.simulation_time:.2f}s', 36, (0, 0, 0))
            self.screen.blit(task_time_text, (self.screen_width - 350, 20))


            # # Call draw_decision_making_status from the imported module if it exists
            # if hasattr(decision_making_module, 'draw_decision_making_status'):
            #     decision_making_module.draw_decision_making_status(screen, agent)  

            # Check if all tasks are completed
            if self.mission_completed:
                text_rect = self.mission_completed_text.get_rect(center=(self.screen_width // 2, self.screen_height // 2))
                self.screen.blit(self.mission_completed_text, text_rect)

            pygame.display.flip()
            self.clock.tick(self.sampling_freq*self.speed_up_factor)




        elif self.rendering_mode == "Terminal":
            print(f"Time: {self.simulation_time:.2f}, Tasks left: {len(self.tasks)}")
            if self.simulation_time - self.last_print_time > 0.5:                    
                self.last_print_time = self.simulation_time
                
            if self.mission_completed:                    
                print(f'MISSION COMPLETED')
                self.running = False            

        else: # if rendering_mode is None
            if self.mission_completed:
                print(f'[{self.simulation_time:.2f}] MISSION COMPLETED')
                self.running = False                


    def close(self):
        pygame.quit()
        self.save_results()

    def save_results(self):
        # Save gif
        if self.save_gif and self.rendering_mode == "Screen":        
            self.recording = False
            print("Recording stopped.")
            self.result_saver.save_gif(self.frames)          
     

        # Save time series data
        if self.save_timewise_result_csv:        
            csv_file_path = self.result_saver.save_to_csv("timewise", self.data_records, ['time', 'agents_total_distance_moved', 'agents_total_task_amount_done', 'remaining_tasks', 'tasks_total_amount_left'])          
            self.result_saver.plot_timewise_result(csv_file_path)
        
        # Save agent-wise data            
        if self.save_agentwise_result_csv:        
            variables_to_save = ['agent_id', 'task_amount_done', 'distance_moved']
            agentwise_results = self.result_saver.get_agentwise_results(self.agents, variables_to_save)                        
            csv_file_path = self.result_saver.save_to_csv('agentwise', agentwise_results, variables_to_save)
            
            self.result_saver.plot_boxplot(csv_file_path, variables_to_save[1:])

        # Save yaml: TODO - To debug
        # if self.save_config_yaml:                
            # self.result_saver.save_config_yaml()           


    def generate_tasks_if_needed(self):
        """Generate new tasks dynamically based on configuration."""
        if self.generation_count < self.max_generations:
            if self.simulation_time - self.last_generation_time >= self.generation_interval:
                new_task_id_start = len(self.tasks)
                new_tasks = generate_tasks(task_quantity=self.tasks_per_generation, task_id_start=new_task_id_start)
                self.tasks.extend(new_tasks)
                self.last_generation_time = self.simulation_time
                self.generation_count += 1
                if self.rendering_mode != "None":
                    print(f"[{self.simulation_time:.2f}] Added {self.tasks_per_generation} new tasks: Generation {self.generation_count}.")

    def handle_keyboard_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                    self.running = False
                elif event.key == pygame.K_p:
                    self.game_paused = not self.game_paused
                elif event.key == pygame.K_r:
                    if not self.recording:
                        self.recording = True
                        self.frames = [] # Clear any existing frames
                        self.last_frame_time = self.simulation_time
                        print("Recording started...") 
                    else:
                        self.recording = False
                        print("Recording stopped.")
                        self.result_saver.save_gif(self.frames) 
    
    def record_timewise_result(self):
        agents_total_distance_moved = sum(agent.distance_moved for agent in self.agents)
        agents_total_task_amount_done = sum(agent.task_amount_done for agent in self.agents)
        remaining_tasks = len([task for task in self.tasks if not task.completed])
        tasks_total_amount_left = sum(task.amount for task in self.tasks)
        
        self.data_records.append([
            self.simulation_time, 
            agents_total_distance_moved,
            agents_total_task_amount_done,
            remaining_tasks,
            tasks_total_amount_left
        ])        

    def record_screen_frame(self):
        # Capture frame for recording
        if self.simulation_time - self.last_frame_time > 1.0/self.gif_recording_fps: # Capture frame if 0.5 seconds elapsed
            frame = pygame.surfarray.array3d(self.screen)
            self.frames.append(frame)            
            self.last_frame_time = self.simulation_time                    