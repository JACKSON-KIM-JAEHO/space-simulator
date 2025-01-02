from modules.utils import config
# MY_PARAMETER = config['decision_making']['my_decision_making_plugin']['my_parameter']

# Define decision-making class
class MyDecisionMakingClass:
    def __init__(self, agent):
        self.agent = agent        
        self.assigned_task = None
        self.satisfied = False # Rename if necessary
        # Define any variables if necessary

    def decide(self, blackboard):
        # Place your decision-making code for each agent
        '''
        Output: 
            - `task_id`, if task allocation works well
            - `None`, otherwise
        '''  
        assigned_task_id = blackboard.get('assigned_task_id', None)
        if assigned_task_id is None:
            available_tasks = blackboard.get('local_tasks_info', [])
            start_tasks = [
                task for task in available_tasks 
                if task.is_start and not task.completed and not task.assigned
            ]

            if start_tasks:
                unassigned_tasks = [task for task in start_tasks if not task.assigned]
                if unassigned_tasks:
                    closest_task = min(
                        unassigned_tasks, 
                        key=lambda task: self.agent.position.distance_to(task.position)
                    )
                    assigned_task_id = closest_task.task_id
                    closest_task.assigned = True
                    blackboard['assigned_task_id'] = assigned_task_id
                    end_task_id = closest_task.get_pair_task_id()
                    blackboard['end_task_id'] = end_task_id
                    return assigned_task_id

            return None

        else:
            end_task_id = blackboard.get('end_task_id')
            if end_task_id is None:
                current_task = next(
                    (task for task in blackboard.get('local_tasks_info', []) if task.task_id == assigned_task_id),
                    None
                )
                if current_task:
                    end_task_id = current_task.get_pair_task_id()
                    blackboard['end_task_id'] = end_task_id
            return end_task_id


