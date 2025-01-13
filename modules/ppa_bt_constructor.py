# ppa_bt_expansion.py
from modules.base_bt_nodes import * # 확인 후 수정
import xml.etree.ElementTree as ET
import csv
import importlib
bt_module = importlib.import_module(config.get('scenario').get('environment') + ".bt_nodes")

# Algorithm 2: LoadLibrary Function
def load_library(csv_file_path):
    ppa_library = {}
    with open(csv_file_path, "r") as csvfile:
        csv_data = csv.DictReader(csvfile)
        for row in csv_data:
            Post_condition = row["Post_condition"]
            Action = row["Action"]
            Pre_conditions = row["Pre_conditions"].split(",") if row["Pre_conditions"] else []
            ppa_library[Post_condition] = {
                "action": Action,
                "pre_conditions": Pre_conditions
            }
    print(f"ppa_library: {ppa_library}")
    return ppa_library


# Algorithm 3: ExpandBehaviorTree Function
def expand_behavior_tree(tree, failed_condition, ppa_library):
    if failed_condition in ppa_library:
        ppa_fail_entry = ppa_library[failed_condition]
        print(f"[DEBUG] Expanding BT for failed condition: {failed_condition}")
        ppa_bt = generate_ppa_bt(failed_condition, ppa_fail_entry)
        tree = replace_node_with_ppa_bt(tree, failed_condition, ppa_bt)
        save_tree_as_xml(tree, "agent_bt_temp.xml")
    return tree


# Algorithm 4: GeneratePPA_BT Function
def generate_ppa_bt(post_condition, ppa_fail_entry):
    print(f"[DEBUG] Generating PPA-BT for Post_condition: {post_condition}")

    # Create Fallback Node
    fallback = Fallback("Fallback", children=[])

    # Add Pre-conditions as Sequence Node
    sequence = Sequence("Sequence", [])
    for pre_condition in ppa_fail_entry["pre_conditions"]:
        if pre_condition:
            condition_class = getattr(bt_module, pre_condition)
            condition_node = condition_class(pre_condition, None)
            sequence.children.append(condition_node)

    # Add Action Node
    action_class = getattr(bt_module, ppa_fail_entry["action"])
    action_node = action_class(ppa_fail_entry["action"], None)
    sequence.children.append(action_node)

    # Add to Fallback Node
    # fallback.children.append(sequence)

    # Add Post-condition Node to Fallback
    condition_class = getattr(bt_module, post_condition)
    condition_node = condition_class(post_condition, None)
    condition_node.set_expanded()
    fallback.children.append(condition_node)
    fallback.children.append(sequence)

    return fallback


# Algorithm 5: ReplaceNodeWithPPA_BT Function
def replace_node_with_ppa_bt(tree, failed_condition, ppa_bt):
    if tree.name == failed_condition:
        print(f"[DEBUG] Replacing node: {failed_condition}")
        return ppa_bt

    if hasattr(tree, "children"):
        new_children = []
        for child in tree.children:
            new_child = replace_node_with_ppa_bt(child, failed_condition, ppa_bt)
            new_children.append(new_child)
        tree.children = new_children

    return tree

# Utility: SaveTreeAsXML Function
def save_tree_as_xml(tree, file_path):
    def node_to_xml(node, visited=None):
        if visited is None:
            visited = set()

        # Prevent circular reference
        if id(node) in visited:
            print(f"[WARNING] Circular reference detected for node: {node.name}")
            return None

        visited.add(id(node))

        # Create XML Element
        element = ET.Element(node.name)
        print(f"[DEBUG] Processing node: {node.name}")
        if hasattr(node, "children"):
            for child in node.children:
                child_xml = node_to_xml(child, visited)
                if child_xml is not None:
                    element.append(child_xml)
        return element

    # Convert tree to XML
    root = node_to_xml(tree)

    # Save XML to file
    xml_tree = ET.ElementTree(root)
    xml_tree.write(file_path, encoding="utf-8", xml_declaration=True)

