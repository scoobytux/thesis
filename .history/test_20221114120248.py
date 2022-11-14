import numpy as np
import pickle
import sys

from xmlrpc.client import Boolean
from Tree import Tree, Node
from RRTree import RRTree
from RRT_draw_lib import Plot_RRT
from Robot_math_lib import *
from Robot_class import Robot
from RRT_user_input import menu_RRT
from Program_config import *
from Obstacles import Obstacles
from Tree import Node, Tree
from numpy.random import default_rng

sys.setrecursionlimit(12000)
rng = default_rng()
uniform_float_arr = rng.uniform(0,1,1000)
class RRTree_star(RRTree):

    """ RRTree class from Tree class """
    def __init__(self, root, step_size = 5, radius=5, random_area=(0, 100), sample_size = 100):
        super().__init__(root, step_size, radius, random_area, sample_size)

    ''' add node to RRTree , return new_node and its neighbour_node(s)'''
    def add_node_RRTstar(self, accepted_coordinate):
        # find all neighbours of node_coordinate
        neighbour_nodes = self.neighbour_nodes(accepted_coordinate, self.radius)
        # pick nearest neighbour as new_node's parent
        nearest_neighbour_node = self.neighbours_smallest_cost(accepted_coordinate, neighbour_nodes)


        if nearest_neighbour_node is not None: # found a neighbour to link to 
            # allocate new node then link to RRTree
            new_node = Node(accepted_coordinate)
            new_node.add_neighbours(neighbours=neighbour_nodes)
            self.add_node(new_node=new_node)
            self.add_edge(parent_node=nearest_neighbour_node, node=new_node)
            return new_node, neighbour_nodes, nearest_neighbour_node
        return None, None, None        

    def build(self,  goal_coordinate, plotter: Plot_RRT=None, obstacles=None, show_animation=False):
        first_saw_goal = False

        for i in range(1, self.sampling_size):
            
            # generate random coordinate in sampling area = [min, max]
            rand_coordinate = self.random_coordinate()
            
            # orient to goal sometime :))
            if i % 5 == 0 and not self.reach_goal: # bias to goal sometime
                rand_coordinate = np.array(goal_coordinate)

            # bring closer random coordinate to tree
            accepted_coordinate_in_float = self.bring_closer(rand_coordinate=rand_coordinate)
            accepted_coordinate = tuple(int(x) for x in accepted_coordinate_in_float)

            
            # if tree first saw given goal , instead of adding new random , add goal
            if not first_saw_goal:
                nn_goal = self.saw_goal(goal_coordinate)    # return nearst neighbour node of goal
                if nn_goal is not None: # existing a node nearby goal
                    first_saw_goal = True
                    self.reach_goal = True
                    accepted_coordinate = goal_coordinate
            
            # add and link node to tree
            new_node, neighbour_nodes, nearest_neighbour_node  = self.add_node_RRTstar(accepted_coordinate)

            ''' rewire for RRT* '''
            self.rewire(node=new_node, neighbour_nodes=neighbour_nodes)
                
            if self.reach_goal:
                goal_node = self.get_node_by_coords(goal_coordinate)
                self.path_to_goal = self.path_to_root(goal_node)
                self.total_goal_cost = goal_node.cost

            ''' for display '''
            if i == self.sampling_size - 1:
                plotter.build_tree_animation(num_iter= i, Tree= self, obstacles=obstacles,  goal_coords=goal_coordinate, \
                    start_coords=self.root.coords, rand_coordinate= rand_coordinate, rand_node=new_node, 
                    neighbour_nodes=neighbour_nodes, nearest_neighbour_node=nearest_neighbour_node, color_tree=TreeColor.by_cost)
    
    # @Tu
    def get_visited_neighbor_nodes(self, neighbour_nodes, obstacles: Obstacles):
        if neighbour_nodes is None:
            return

        visited_neighbor_nodes = []
        for node in neighbour_nodes:
            collision = obstacles.check_point_collision(point=node.coords,\
                            obstacles_line_segments=obstacles.obstacles_line_segments)
            if not collision:
                visited_neighbor_nodes.append(node)
                node.set_visited()
            else:
                node.set_inactive()
        return visited_neighbor_nodes
    
    def draw_RRT_star(self,  goal_coordinate, start_coordinate, plotter: Plot_RRT=None, obstacles=None):
        plotter.build_RRT_star(num_iter= self.sampling_size - 1, Tree=self, obstacles=obstacles, goal_coords=goal_coordinate, \
                    start_coords=start_coordinate, color_tree=TreeColor.by_cost)

# @ Tu
HM_EPISODES = 700
GOAL_REWARD = 5000
EPS_DECAY = 0.99  # Every episode will be epsilon*EPS_DECAY
LEARNING_RATE = 0.1
DISCOUNT = 0.95
epsilon = 0.9



def handle_q_table(save=Boolean, save_q_table={}):
    #save q_table
    if save:
        with open("qtable1.pickle", "wb") as f:
            pickle.dump(save_q_table, f)
        return

    # initialize the q-table#
    q_table = {}
    try:
        with open("qtable1.pickle", "rb") as f:
            q_table = pickle.load(f)
    except:
        q_table = {}
    return q_table

def filter_path_to_neighbor_nodes(robot=Robot, current_node=Node , visited_neighbor_nodes= [], obstacles= Obstacles):
    temp_filter =[]
    line_segments = []
    for node in visited_neighbor_nodes:
        line_segments.append([current_node.coords,node.coords])
    temp_filter = robot.check_neighbor_nodes_path(line_segments,obstacles,visited_neighbor_nodes)
    return temp_filter      

def print_shortest_path_length(shortest_path_length,total_path_length):
    if (shortest_path_length > total_path_length):  
        shortest_path_length = total_path_length
    print("shortest path length:" , shortest_path_length)    
    return shortest_path_length
 
def reach_goal(goal, robot=Robot):
    if robot.coordinate == goal:
        return True
    return False

def reset_node_checkin(Tree = Tree):
    nodes = Tree.all_nodes()
    for node in nodes:
        node.checkin = False
 
def get_total_path_length(path_to_goal):
    total_length = 0
    for i in range(len(path_to_goal) - 1):
        total_length += point_dist(path_to_goal[i].coords, path_to_goal[i+1].coords)
    return round(total_length,2)    

def ranking_list(list = []):
    seq  = sorted(list)
    index = [seq.index(v) for v in list]
    return index

def get_node_index(check_node , neighbor_nodes = []):
    for node in range(len(neighbor_nodes)):
        if check_node.coords == neighbor_nodes[node].coords:
            node_idx = node
            return node_idx

def middle_value_in_list(list=[]):
    middle_value = 0
    for val in list:
        middle_value += val
    middle_value = middle_value/len(list)
    return middle_value    

def get_further_point_line_segment(node,ls):
    distance_1 = point_dist(node.coords,ls[0])
    distance_2 = point_dist(node.coords,ls[1])
    if distance_1 < distance_2:
        return distance_2
    else:
        return distance_1

    
def evaluate_reward(Tree = Tree, current_node = Node, next_node = Node , visited_neighbor_nodes=[], avg_neighbors_to_obs=[],check=Boolean,nearest_ls=[]):
    reward = 0
    next_node_idx = get_node_index(next_node,visited_neighbor_nodes)
    current_node_to_further_ls = get_further_point_line_segment(current_node, nearest_ls)
    next_node_to_further_ls = get_further_point_line_segment(next_node, nearest_ls)
    
    # first condition
    # penalty if return to a checkin node
    if next_node.checkin:
        reward -= 1000
    else:            
        # second condition 
        #variable to check degree between current node and next node
        current_node_degree = len(Tree.path_to_root(current_node)) - 1
        next_node_degree = len(Tree.path_to_root(next_node)) - 1
        degree = current_node_degree - next_node_degree       
        if degree >= 1: # next node belongs to parent degree of current node
            reward += degree*5
        elif degree <= -1: # next node belongs to children degree of current node
            reward -= abs(degree)*5
        elif degree == 0: # next node has the same degree of current node
            reward += 3
        
        # third condition
        neighbors_length_to_root =Tree.distances(Tree.root.coords, visited_neighbor_nodes)   
        # neighbors_length_to_current = Tree.distances(current_node.coords, visited_neighbor_nodes)
        # neighbors_avg_length = np.array(neighbors_length_to_current) + np.array(neighbors_length_to_root)
        ranking_neighbors = ranking_list(neighbors_length_to_root)
        
        middle_value_neighbors = middle_value_in_list(ranking_neighbors)
     
            
        # fourth condition 
        ranking_neighbors_distance_to_obs = ranking_list(avg_neighbors_to_obs) 
        
        middle_value_neighbors_to_obs = middle_value_in_list(ranking_neighbors_distance_to_obs)
        if (ranking_neighbors_distance_to_obs[next_node_idx] >= middle_value_neighbors_to_obs):
            reward -= ranking_neighbors_distance_to_obs[next_node_idx]*50     
        else:
            reward += (len(ranking_neighbors_distance_to_obs) - ranking_neighbors_distance_to_obs[next_node_idx])*50 
         
        if next_node_to_further_ls >= current_node_to_further_ls:  
            if (ranking_neighbors[next_node_idx] >= middle_value_neighbors):
                reward -= (ranking_neighbors[next_node_idx] - middle_value_neighbors)*15 
            else:
                reward += (middle_value_neighbors - ranking_neighbors[next_node_idx])*15
            if not check:    
                current_to_root = point_dist(current_node.coords,Tree.root.coords)  
                next_to_root = point_dist(next_node.coords,Tree.root.coords)
                distance = current_to_root - next_to_root
                if distance >= 0: 
                    reward += distance*10 
                else:
                    reward -= distance0       
    return reward

def run_by_rrtstar(robot=Robot,Tree=Tree, path_to_goal=[]):
    obs_ls = []
    robot_current_node = Tree.get_node_by_coords(robot.get_robot_coords())
    # Get robot path from current node to goal based on RRT*
    Tree.path_to_goal = Tree.path_to_root(robot_current_node)
    
    # Move along RRT* path until seeing obstacles
    for idx in range(len(Tree.path_to_goal)):
        node = Tree.path_to_goal[idx]
        node.set_checkin()  # checkin node that already go through
        robot.coordinate = node.coords
        # visualize
        path_to_goal.append(node)
        if len(Tree.path_to_goal) - idx <= 1:
            break
        next_node = Tree.path_to_goal[idx+1]
        is_see_obstacles, obs_ls = robot.check_intersection_obs(obstacles, node, next_node)
        if is_see_obstacles:
            robot.generate_grid_coordinates()
            break 
    return obs_ls    
                
def run_by_reinforcement_learning(goal, vision_range, robot, Tree, obstacles, q_table, obs_ls):
    robot_action = 0 
    robot_action_idx = 0
    reward = 0
    avg_neighbors_to_obs = []
    
    robot_state = robot.get_robot_coords()
    current_node = Tree.get_node_by_coords(robot_state)
    neighbor_nodes = Tree.neighbour_nodes(robot_state, vision_range)
    
    # filter neighbor nodes that is inside obstacles
    visited_neighbor_nodes = Tree.get_visited_neighbor_nodes(neighbor_nodes, obstacles)
    # filter neighbor nodes path
    visited_neighbor_nodes = filter_path_to_neighbor_nodes(robot,current_node,visited_neighbor_nodes,obstacles)
    # average neighbor nodes distance to obstacle
    avg_neighbors_to_obs = robot.avg_neighbors_distance_to_obs(visited_neighbor_nodes,obs_ls)
    if not robot_state in q_table:
        q_table[robot_state] = [0 for i in range(len(visited_neighbor_nodes))]
    
    #take move base on highest q-value
    idx = rng.integers(0,len(uniform_float_arr))
    if uniform_float_arr[idx] > epsilon: 
        robot_action_idx = np.argmax(q_table[robot_state])
        chosen_node_coords = visited_neighbor_nodes[robot_action_idx].coords
        for idx in range(len(robot.grid_coordinates)):
            if chosen_node_coords == robot.grid_coordinates[idx]:
                robot_action = idx
                break
        
    # take random move
    
    else:
        robot_action_idx = np.random.randint(len(visited_neighbor_nodes))
        for idx in range(len(robot.grid_coordinates)):
            if visited_neighbor_nodes[robot_action_idx].coords == robot.grid_coordinates[idx]:
                robot_action = idx
                break
  
        
    # Take the action!
    robot.action(robot_action)              
    robot.is_reach_goal(goal)
    robot_next_state = robot.get_robot_coords()
    next_node = Tree.get_node_by_coords(robot_next_state)
    if robot.reach_goal:
        reward = GOAL_REWARD
    else:
        next_node_path = Tree.path_to_root(next_node)
        check , _ = robot.check_intersection_obs(obstacles, next_node_path[0],next_node_path[1])
        nearest_ls = robot.nearest_line_segment(current_node, obs_ls)
        reward = evaluate_reward(Tree, current_node, next_node, visited_neighbor_nodes, avg_neighbors_to_obs,check,nearest_ls)
    
    next_node.set_checkin() #checkin node
        
    # update q table 
    
    next_neighbor_nodes = Tree.neighbour_nodes(robot_next_state, vision_range)
    # filter neighbor nodes that is inside obstacles
    next_visited_neighbor_nodes = Tree.get_visited_neighbor_nodes(next_neighbor_nodes, obstacles)
    # filter neighbor nodes path
    next_visited_neighbor_nodes = filter_path_to_neighbor_nodes(robot,next_node,next_visited_neighbor_nodes,obstacles)
    
    if not robot_next_state in q_table:
        q_table[robot_next_state] = [0 for i in range(len(next_visited_neighbor_nodes))]
    max_future_q = np.max(q_table[robot_next_state])
    current_q = q_table[robot_state][robot_action_idx]
    if reward == GOAL_REWARD:
        new_q = GOAL_REWARD
    else:
        new_q = (1 - LEARNING_RATE) * current_q + LEARNING_RATE * (reward + DISCOUNT * max_future_q)
        q_table[robot_state][robot_action_idx] = new_q
    
    return reward
        
def train(start, goal, obstacles=Obstacles(), vision_range=5, Tree=Tree, view_map=False):
    save_q_table = True
    total_path_length = 0
    shortest_path_length = 1000000
    q_table = handle_q_table(not save_q_table)
    if view_map:
        global HM_EPISODES
        HM_EPISODES = 1
    for episode in range(HM_EPISODES):
        episode_reward = 0
        robot = Robot(start=start, goal=goal, vision_range=vision_range)
        
        # path to goal each episode
        path_to_goal = []

        while True:
            obs_ls = run_by_rrtstar(robot, Tree, path_to_goal)

            # reach goal
            if reach_goal(goal, robot):
                break
           
            reward = run_by_reinforcement_learning(goal, vision_range, robot, Tree, obstacles,q_table,obs_ls)
            if not view_map:
                handle_q_table(save_q_table, q_table)
            episode_reward += reward
            
        Tree.path_to_goal = path_to_goal
        total_path_length = get_total_path_length(Tree.path_to_goal)
        Tree.total_goal_cost = total_path_length
        print("Episode:", episode+1,", node:", start, ", total path length:", total_path_length)        
        shortest_path_length = print_shortest_path_length(shortest_path_length,total_path_length)
        
        reset_node_checkin(Tree)
        total_path_length = 0
        
        global epsilon 
        epsilon *= EPS_DECAY
        
def choose_exist_node(input_node_coords, Tree = Tree):
    input_coords = ()
    nearest_node = 0
    nodes_coords = Tree.all_nodes_coordinate()
    for node_coords in nodes_coords:
        temp_distance = point_dist(input_node_coords, node_coords)
        if nearest_node == 0 or nearest_node >= temp_distance:
            if temp_distance == 0:
                return node_coords
            nearest_node = temp_distance
            input_coords = node_coords
    return input_coords        

def get_nearest_node(input_node_coords, nodes_coords, checked_nodes_coords = []):
    nearest_coords = ()
    nearest_node = 0
    checked = False
    for node_coords in nodes_coords:
        for checked_node_coords in checked_nodes_coords:
            if node_coords == checked_node_coords:
                checked = True
                break
        if not checked:    
            temp_distance = point_dist(input_node_coords, node_coords)
            if nearest_node == 0 or nearest_node > temp_distance:
                nearest_node = temp_distance
                nearest_coords = node_coords
        else:
            checked = False
            continue        
    return nearest_coords

    
def check_node_obs(Tree = Tree, input_node_coords=(), obstacles = Obstacles, checked_nodes_coords= []):
    nodes_coords = Tree.all_nodes_coordinate()
    nearest_node_coords = input_node_coords
    check_in_obs = True
    while check_in_obs:
        check_in_obs = obstacles.check_point_collision(nearest_node_coords, obstacles.obstacles_line_segments)
        if check_in_obs:
            checked_nodes_coords.append(nearest_node_coords)
            nearest_node_coords = get_nearest_node(input_node_coords, nodes_coords, checked_nodes_coords) 
 
    return nearest_node_coords        
                
if __name__ == '__main__':
    
    # try read tree from rrt_star.pickle
        
    try:
        with open('rrt_star.pickle', 'rb') as f: 
            RRT_star = pickle.load(f)
    except:
        read_tree = False
        print("Create and save the tree ...")
    else:
        read_tree = True
    
    ''' initial parameters '''
    # get user input
    menu_result = menu_RRT()
    step_size = menu_result.step_size
    radius = menu_result.radius
    sample_size = menu_result.ss
    map_name = menu_result.m
    world_name = None
    view_map = menu_result.view
    ''' Running '''
    # set same window size to capture pictures
    plotter = Plot_RRT(title="Rapidly-exploring Random Tree Star (RRT*)")
    plotter.set_equal()

    ''' get obstacles data whether from world (if indicated) or map (by default)'''
    obstacles = Obstacles()
    obstacles.read(world_name, map_name)
    obstacles.line_segments()
    size = 70   
    random_area = ([0, 0], [size, size])
            
    if not read_tree:
        start_cooridinate = menu_result.sx, menu_result.sy
        goal_coordinate = menu_result.gx, menu_result.gy

        '''
            build tree
        '''
        start_node = Node(start_cooridinate, cost=0)            # initial root node, cost to root = 0
        RRT_star = RRTree_star(root=start_node, step_size=step_size, radius=5, 
                        random_area=random_area, sample_size=sample_size)
        RRT_star.build(goal_coordinate=goal_coordinate, plotter=plotter, obstacles=obstacles, show_animation=True)
        
        ''' 
            save the tree
        '''
        with open('rrt_star.pickle', 'wb') as f:
            pickle.dump(RRT_star, f)

    else:
        input_array = [(8, 9), (29, 4), (46, 2),  (55, 0), (64, 10), (54, 38), (35, 39), (28, 48), (5, 42), (2, 53)]
        for idx in range(len(input_array)):
            epsilon = 0.9
            start_cooridinate = input_array[idx+0]
            print("input node:",start_cooridinate)       
            #check if input node exist
            start_cooridinate = choose_exist_node(start_cooridinate, RRT_star)
            goal_coordinate = RRT_star.root.coords
            #check if start and goal collide obstacle
            start_cooridinate = check_node_obs(RRT_star, start_cooridinate, obstacles)
            print("start node:",start_cooridinate)
            
            ''' 
                train the robot , use the sample tree
            '''
            train(start=start_cooridinate, goal=goal_coordinate,\
                obstacles=obstacles, vision_range=5,Tree=RRT_star, view_map=view_map)
                
            if view_map:
                print("View path ...")
                break
            else:
                if idx < len(input_array) - 1:
                    print("Preparing train next node...")
                else:
                    print("Finish training.") 
                    
            break
        ''' 
        draw the result: obstacles + RRT* + robot path 
        ''' 
        RRT_star.draw_RRT_star(goal_coordinate=goal_coordinate, start_coordinate=start_cooridinate,\
            plotter=plotter, obstacles=obstacles)    
    plotter.show()

