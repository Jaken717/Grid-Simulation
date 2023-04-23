# -*- coding: utf-8 -*-
"""
Created on Wed Mar 23 23:48:35 2022

@author: Hamil
"""

import re
import numpy as np

# open the glm file
feeder_name = 'R2-12-47-3'
filename = 'Feeder_1_Solar_100_mod.glm'
readfile = open(filename,'r')
contents = readfile.read()

# get everything before the first object
first_obj_ind = contents.find('object')
header = contents[0:first_obj_ind]

# get all objects
objects = re.findall('object.*?\{.*?\}(?!;)',contents,re.DOTALL) 


nodes = []
branches = []
configs = []
misc = []

node_objs = {}
branch_objs = {}
config_objs = {}
misc_objs = {}

node_types = 'node|meter|load|triplex_node|triplex_meter|triplex_load|'\
             'capacitor|house|inverter|ZIPload|waterheater'
branch_types = 'link|line|overhead_line|underground_line|triplex_line|'\
              'transformer|regulator|fuse|switch'
config_types = 'configuration|spacing|conductor'
misc_types = 'climate|recorder|billdump|multi_recorder|player|collector'
              
node_match_str = 'object (' + node_types + ') \{'
branch_match_str = 'object (' + branch_types + ') \{'
config_match_str = 'object .*?(' + config_types + ') \{'
misc_match_str = 'object (' + misc_types + ') \{'

unnamed_branch_cnt = 0

# loop through all the objects
for obj in objects:
    
    # find all nodes
    if re.match(node_match_str,obj,re.DOTALL):
        name_match = re.search('name .*?;',obj,re.DOTALL)
        name = name_match.group().replace('name ','').strip(';')
        nodes.append(name)
        node_objs[name] = obj
        
    # find all branches
    elif re.match(branch_match_str,obj,re.DOTALL):
        name_match = re.search('name .*?;',obj,re.DOTALL)
        if name_match is not None:
            name = name_match.group().replace('name ','').strip(';')
        else:
            unnamed_branch_cnt = unnamed_branch_cnt + 1
            name = 'unnamed_branch_' + str(unnamed_branch_cnt) 
        branches.append(name)
        branch_objs[name] = obj
        
    # find all configs
    elif re.match(config_match_str,obj,re.DOTALL):
        #name_match = re.search(config_match_str,obj,re.DOTALL)
        #name = name_match.group().replace('object ','').strip(';{ ')
        #if 'triplex_line_conductor:' in name:
           # name_match = re.search('name .*?;',obj,re.DOTALL)
            #name = name_match.group().replace('name ','').strip(';')
        name_match = re.search('name .*?;',obj,re.DOTALL)
        name = name_match.group().replace('name ','').strip(';')
        configs.append(name)
        config_objs[name] = obj
        
    # find misc objs
    if re.match(misc_match_str,obj,re.DOTALL):
        name_match = re.search('file .*?;',obj,re.DOTALL)
        if name_match is not None:
            name = name_match.group().replace('file ','').strip(';{')
        else:
            name_match = re.search('filename .*?;',obj,re.DOTALL)
            name = name_match.group().replace('filename ','').strip(';{')
        misc.append(name)
        misc_objs[name] = obj
        
# make sure we got everything
if (len(nodes)+len(branches)+len(configs)+len(misc)) != len(objects):
    print('WARNING: Missing objects! I found ',len(nodes)+len(branches)+len(configs)+len(misc),' of ',len(objects))
#else:
    #print('I think we got everything.')
    

    
# find nodes that are parented
parents_dict = {}
unique_nodes = nodes.copy()
for node in nodes:
    ndobj = node_objs[node]
    parent_match = re.search('parent .*?;',ndobj,re.DOTALL)
    if parent_match is not None:
        # this node has a parent
        parent = parent_match.group().replace('parent ','').strip(';')
        # add it to the parents dictionary
        if parent in parents_dict:
            children = parents_dict[parent]
            children.append(node)
            parents_dict[parent] = children
        else:
            parents_dict[parent] = [node]
        # remove it from list of unique nodes
        unique_nodes.remove(node)

# extract sdp node data
recog_voltages_ll = [480];
recog_voltages_ln = [7200];
node_data_file = open(filename.replace('.glm','_node_data.txt'),'w')
node_data_file.write('\\\\ Node Data\n\\\\Index, Label, Phases, baseV\n')
nd_indx = 1
sdp_nodes = []
for node in unique_nodes:  
    # find phases
    phases_match = re.search('phases .*?;',node_objs[node],re.DOTALL)
    phases = phases_match.group().replace('phases ','').strip(';')
    # find baseV
    node_type_match = re.search('object .*?\{',node_objs[node],re.DOTALL)
    node_type = node_type_match.group().replace('object ','').strip('\}')
    baseV_match = re.search('nominal_voltage .*?;',node_objs[node],re.DOTALL)
    if 'S' in phases:
        baseV = float(baseV_match.group().replace('nominal_voltage ','').strip(';'))
    else:
        nomV = float(baseV_match.group().replace('nominal_voltage ','').strip(';'))
        if nomV in recog_voltages_ln:
            baseV = nomV
        elif nomV in recog_voltages_ll:
            baseV = nomV/np.sqrt(3)
        else:
            baseV = nomV
            print('WARNING: I don''t recognize the nominal voltage '+str(nomV)+'. Assuming it is L-N.\n')
    linetxt = '{0}, {1}, {2}, {3}\n'
    node_label = node.replace(feeder_name+'_','')
    node_data_file.write(linetxt.format(nd_indx,node_label,phases,baseV))
    sdp_nodes.append(node)
    nd_indx += 1
    '''
    # exclude split-phase nodes
    if 'S' not in phases:
        # find baseV
        node_type_match = re.search('object .*?\{',node_objs[node],re.DOTALL)
        node_type = node_type_match.group().replace('object ','').strip('\}')
        baseV_match = re.search('nominal_voltage .*?;',node_objs[node],re.DOTALL)
        baseV = np.sqrt(3)*float(baseV_match.group().replace('nominal_voltage ','').strip(';'))
        linetxt = '{0}, {1}, {2}, {3}\n'
        node_label = node.replace(feeder_name+'_','')
        node_data_file.write(linetxt.format(nd_indx,node_label,phases,baseV))
        sdp_nodes.append(node)
        nd_indx += 1
    '''
       
    
# extract branch data
branch_data_file = open(filename.replace('.glm','_branch_data.txt'),'w')
branch_data_file.write('\\\\ Branch Data\n\\\\Index, Label, Type, Phases, From, To, ShuntImpedance, PowerRating, ConnectionType\n')
br_indx = 1
for branch in branches: 
    branch_label = branch.replace(feeder_name+'_','')
    # find type
    branch_type_match = re.search('.*?_',branch_label)
    branch_type_short = branch_type_match.group().strip('_')
    if re.match('(ul)|(ol)',branch_type_short):
        branch_type = 'LINE'
    elif re.match('tl',branch_type_short):
        branch_type = 'TRIL'
    elif re.match('xfmr',branch_type_short):
        branch_type = 'XFRMR'
    elif re.match('switch',branch_type_short):
        branch_type = 'SWITCH'
    elif re.match('fuse',branch_type_short):
        branch_type = 'FUSE'
    elif re.match('load',branch_type_short) and ('CTTF' in branch_label):
        # this is a stripmall transformer
        branch_type = 'XFRMR'
    elif re.match('load',branch_type_short) and ('ohl' in branch_label):
        # this is an ohl in a commercial load
        branch_type = 'LINE'
    elif re.match('unnamed',branch_type_short):
        unbr_type_match = re.search('object .*? \{',branch_objs[branch],re.DOTALL)
        unbr_type = unbr_type_match.group().replace('object ','').strip(' \{')
        if re.match('overhead_line',unbr_type):
            branch_type = 'LINE'
        else:
            print('WARNING: I don''t know the unnamed branch type '+unbr_type+'.\n')
    else:
        branch_type = 'UNKNOWN'
        print('WARNING: I don''t know the branch type '+branch_type_short+'.\n') 
    # find phases
    phases_match = re.search('phases .*?;',branch_objs[branch],re.DOTALL)
    phases = phases_match.group().replace('phases ','').strip(';')
    # find from
    from_match = re.search('from .*?;',branch_objs[branch],re.DOTALL)
    from_node = from_match.group().replace('from ','').strip(';')
    if from_node not in sdp_nodes:
        # find parent node
        find_parent_iter = 0
        parent = from_node
        while (parent not in sdp_nodes) and (find_parent_iter < 1000):
            parent_match = re.search('parent .*?;',node_objs[parent],re.DOTALL)
            parent = parent_match.group().replace('parent ','').strip(';')
            find_parent_iter += 1
        if find_parent_iter >= 1000:
            print('WARNING: Can''t find parent of node '+node+'.\n')
        from_node_indx = sdp_nodes.index(parent)+1
    else:
        from_node_indx = sdp_nodes.index(from_node)+1
    # find to
    to_match = re.search('to .*?;',branch_objs[branch],re.DOTALL)
    to_node = to_match.group().replace('to ','').strip(';')
    to_node_indx = sdp_nodes.index(to_node)+1
    # get any extra parameters
    shunt_imp = 'N/A'
    prating = 'N/A'
    connect_type = 'N/A'
    if (branch_type == 'XFRMR'):
        # get the transformer configuration
        config_match = re.search('configuration .*?;',branch_objs[branch],re.DOTALL)
        config = config_match.group().replace('configuration ','').strip(';')
        config_object = config_objs[config]
        # get the shunt impedance
        shunt_match = re.search('shunt_impedance .*?;',config_object,re.DOTALL)
        shunt_imp = shunt_match.group().replace('shunt_impedance ','').strip(';')
        # get the transformer rating
        prating_match = re.search('power_rating .*?;',config_object,re.DOTALL)
        if prating_match is None:
            if 'A' in phases:
                prating_match = re.search('powerA_rating .*?;',config_object,re.DOTALL)
                prating = prating_match.group().replace('powerA_rating ','').strip(';')
            elif 'B' in phases:
                prating_match = re.search('powerB_rating .*?;',config_object,re.DOTALL)
                prating = prating_match.group().replace('powerB_rating ','').strip(';')
            elif 'C' in phases:
                prating_match = re.search('powerC_rating .*?;',config_object,re.DOTALL)
                prating = prating_match.group().replace('powerC_rating ','').strip(';')
        else:
            prating = prating_match.group().replace('power_rating ','').strip(';')
        # get the connection type
        connect_match = re.search('connect_type .*?;',config_object,re.DOTALL)
        connect_type = connect_match.group().replace('connect_type ','').strip(';')
    # write to branch data file
    linetxt = '{0}, {1}, {2}, {3}, {4}, {5}, {6}, {7}, {8}\n'
    branch_data_file.write(linetxt.format(br_indx,branch_label,branch_type,phases,from_node_indx,to_node_indx,shunt_imp,prating,connect_type))
    br_indx += 1
    '''
    # exclude split-phase branches that are not center-tapped xfrms
    if 'S' in phases:
        if branch_type == 'XFRMR':
            # this is a center-tapped transformer so add load data
            # find from node
            from_match = re.search('from .*?;',branch_objs[branch],re.DOTALL)
            from_node = from_match.group().replace('from ','').strip(';')
            from_node_indx = sdp_nodes.index(from_node)+1
            linetxt = '{0}, {1}, {2}, {3}\n'
            load_phases = phases.replace('S','N')
            load_data_file.write(linetxt.format(ld_indx,branch_label,from_node_indx,load_phases))
            ld_indx += 1
    else:
        # not a split-phase branch
        # find from
        from_match = re.search('from .*?;',branch_objs[branch],re.DOTALL)
        from_node = from_match.group().replace('from ','').strip(';')
        from_node_indx = sdp_nodes.index(from_node)+1
        # find to
        to_match = re.search('to .*?;',branch_objs[branch],re.DOTALL)
        to_node = to_match.group().replace('to ','').strip(';')
        to_node_indx = sdp_nodes.index(to_node)+1
        linetxt = '{0}, {1}, {2}, {3}, {4}, {5}\n'
        branch_data_file.write(linetxt.format(br_indx,branch_label,branch_type,phases,from_node_indx,to_node_indx))
        br_indx += 1
    '''

# extract load data
load_data_file = open(filename.replace('.glm','_load_data.txt'),'w')
load_data_file.write('\\\\ Load Data\n\\\\Index, Label, Node, Phases, Model\n')
ld_indx = 1
for node in node_objs:  
    node_type_match = re.search('object .*?\{',node_objs[node],re.DOTALL)
    node_type = node_type_match.group().replace('object ','').strip('\}')
    if 'house' in node_type:
        # find parent node
        find_parent_iter = 0
        parent = node
        while (parent not in sdp_nodes) and (find_parent_iter < 1000):
            parent_match = re.search('parent .*?;',node_objs[parent],re.DOTALL)
            parent = parent_match.group().replace('parent ','').strip(';')
            find_parent_iter += 1
        if find_parent_iter >= 1000:
            print('WARNING: Can''t find parent of node '+node+'.\n')
        parent_indx = sdp_nodes.index(parent)+1
        # find phases
        phases_match = re.search('phases .*?;',node_objs[parent],re.DOTALL)
        phases = phases_match.group().replace('phases ','').strip(';')
        linetxt = '{0}, {1}, {2}, {3}, HOUSE\n'
        load_label = node.replace(feeder_name+'_','')
        load_data_file.write(linetxt.format(ld_indx,load_label,parent_indx,phases))
        ld_indx += 1
    elif 'triplex_load' in node_type:
        # find parent node
        find_parent_iter = 0
        parent = node
        while (parent not in sdp_nodes) and (find_parent_iter < 1000):
            parent_match = re.search('parent .*?;',node_objs[parent],re.DOTALL)
            parent = parent_match.group().replace('parent ','').strip(';')
            find_parent_iter += 1
        if find_parent_iter >= 1000:
            print('WARNING: Can''t find parent of node '+node+'.\n')
        parent_indx = sdp_nodes.index(parent)+1
        # find phases
        phases_match = re.search('phases .*?;',node_objs[parent],re.DOTALL)
        phases = phases_match.group().replace('phases ','').strip(';')
        linetxt = '{0}, {1}, {2}, {3}, HOUSE\n'
        load_label = node.replace(feeder_name+'_','')
        load_data_file.write(linetxt.format(ld_indx,load_label,parent_indx,phases))
        ld_indx += 1

    

# extract DER data
der_data_file = open(filename.replace('.glm','_der_data.txt'),'w')
der_data_file.write('\\\\ DER Data\n\\\\Index, Label, Node, Phases, Rated Powers, Mode\n')
der_indx = 1
for node in node_objs:  
    node_type_match = re.search('object .*?\{',node_objs[node],re.DOTALL)
    node_type = node_type_match.group().replace('object ','').strip('\}')
    if 'triplex_meter' in node_type:
        inv_match = re.search('object inverter \{',node_objs[node],re.DOTALL)
        if inv_match is not None:
            # find parent node - its parent should be a triplex meter
            find_parent_iter = 0
            parent = node
            while (parent not in sdp_nodes) and (find_parent_iter < 1000):
                parent_match = re.search('parent .*?;',node_objs[parent],re.DOTALL)
                parent = parent_match.group().replace('parent ','').strip(';')
                find_parent_iter += 1
            if find_parent_iter >= 1000:
                print('WARNING: Can''t find parent of node '+node+'.\n')
            parent_indx = sdp_nodes.index(parent)+1
            '''
            # next find the transformer to aggregate this der to 
            # the triplex meter parent of this der will be connected to a
            # triplex node with the same number, which is the to node of the 
            # transformer
            for branch in branches:
                # find to node
                to_match = re.search('to .*?;',branch_objs[branch],re.DOTALL)
                to_node = to_match.group().replace('to ','').strip(';')
                if to_node == parent.replace('tm_','tn_'):
                    # find from node
                    from_match = re.search('from .*?;',branch_objs[branch],re.DOTALL)
                    from_node = from_match.group().replace('from ','').strip(';')
                    from_node_indx = sdp_nodes.index(from_node)+1
            '''
            # find phases
            phases_match = re.search('phases .*?;',node_objs[parent],re.DOTALL)
            phases = phases_match.group().replace('phases ','').strip(';')
            # find rated power
            rated_power_match = re.search('rated_power .*?;',node_objs[node],re.DOTALL)
            if rated_power_match is not None:
                rated_power = rated_power_match.group().replace('rated_power ','').strip(';')
            else:
                # must be a constant pf inverter, let's find the floor area of the panel
                floor_area_match = re.search('area .*?;',node_objs[node],re.DOTALL)
                floor_area = floor_area_match.group().replace('area ','').strip(';')
                rated_power = str(float(floor_area)*0.2*92.902)
            if 'AS' in phases:
                rated_powers = '['+rated_power+';0;0]'
            elif 'BS' in phases:
                rated_powers = '[0;'+rated_power+';0]'
            elif 'CS' in phases:
                rated_powers = '[0;0;'+rated_power+']'
            else:
                print('WARNING: I don''t recognize inverter phase type '+phases+'.\n')
            linetxt = '{0}, {1}, {2}, {3}, {4}, {5}\n'
            der_label = node.replace(feeder_name+'_','')
            #der_phases = phases.replace('S','N')
            der_phases = phases
            # find der mode
            if 'VOLT_VAR;' in node_objs[node]: 
                der_mode = 'VOLT_VAR'
            elif 'CONSTANT_PF;' in node_objs[node]: 
                der_mode = 'CONSTANT_PF'
            else:
                print('WARNING: Can''t find this inverter''s mode.\n') 
                der_mode = '???'
            der_data_file.write(linetxt.format(der_indx,der_label,parent_indx,der_phases,rated_powers,der_mode))
            der_indx += 1

      
# add simulation data recorders to write file
writefile = open(filename.replace('.glm','2.glm'),'w')
         
writefile.write(header)        
for obj in objects:
    type_match = re.search('object .*?\{',obj,re.DOTALL)
    objtype = type_match.group().replace('object ','').strip(' \{')
    if objtype == 'triplex_node':
        #print(objtype)
        type_groupid_match = re.search('groupid .*?',obj,re.DOTALL)
        if type_groupid_match is None:
            #print(obj)
            newobj = obj.replace('}','     groupid tnode;\n}') #object triplex_node {\n      groupid tnode;\n
            #print(newobj)
            writefile.write(newobj)
            writefile.write('\n\n')
        else:
            writefile.write(obj)
            writefile.write('\n\n')
    elif objtype == 'triplex_meter':
        #print(objtype)
        type_groupid_match = re.search('groupid .*?',obj,re.DOTALL)
        if type_groupid_match is None:
            #print(obj)
            newobj = obj.replace('}','     groupid tmeter;\n}') #object triplex_node {\n      groupid tnode;\n
            #print(newobj)
            writefile.write(newobj)
            writefile.write('\n\n')
        else:
            writefile.write(obj)
            writefile.write('\n\n')
    elif objtype == 'node':
        #print(objtype)
        type_groupid_match = re.search('groupid .*?',obj,re.DOTALL)
        if type_groupid_match is None:
            #print(obj)
            newobj = obj.replace('}','     groupid node;\n}') #object triplex_node {\n      groupid tnode;\n
            #print(newobj)
            writefile.write(newobj)
            writefile.write('\n\n')
        else:
            writefile.write(obj)
            writefile.write('\n\n')
    else:
        writefile.write(obj)
        writefile.write('\n\n')

    
'''

# voltage and impedance dump    
writefile.write('object voltdump {\n'\
                '     filename '+filename.replace('.glm','2_voltdump.csv')+';\n'\
                '}\n\n')
        
'''
        
writefile.write('object impedance_dump {\n'\
                '     filename '+filename.replace('.glm','2_impdump.xml')+';\n'\
                '}\n\n')
  

# voltage recorders
record_int = '60'
include_res_volt_recorder = True
if include_res_volt_recorder:  
    writefile.write('object group_recorder {\n'\
                                '  group "groupid=House_Meter";\n'\
                                '  property voltage_12;\n'\
                                '  file '+filename.replace('_mod.glm','')+'_ResidentialVoltages.csv;\n'\
                                '  interval '+record_int+';\n'\
                                '  complex_part MAG;\n'\
                                '}\n\n')
        
# house load meter recorders
record_int = '60'
include_res_house_recorders = True
if include_res_house_recorders:
    writefile.write('object group_recorder {\n'\
                                '  group "groupid=House_Meter";\n'\
                                '  property measured_real_power;\n'\
                                '  file '+filename.replace('_mod.glm','')+'_ResidentialRealPowers.csv;\n'\
                                '  interval '+record_int+';\n'\
                                '}\n\n')
    writefile.write('object group_recorder {\n'\
                                '  group "groupid=House_Meter";\n'\
                                '  property measured_reactive_power;\n'\
                                '  file '+filename.replace('_mod.glm','')+'_ResidentialReactivePowers.csv;\n'\
                                '  interval '+record_int+';\n'\
                                '}\n\n')
        
# der input power recorders
record_int = '60'
include_der_recorders = True
if include_der_recorders:
    writefile.write('object group_recorder {\n'\
                                '  group "groupid=Residential_tm_solar";\n'\
                                '  property measured_real_power;\n'\
                                '  file '+filename.replace('_mod.glm','')+'_SolarRealPowers.csv;\n'\
                                '  interval '+record_int+';\n'\
                                '}\n\n')
    writefile.write('object group_recorder {\n'\
                                '  group "groupid=Residential_tm_solar";\n'\
                                '  property measured_reactive_power;\n'\
                                '  file '+filename.replace('_mod.glm','')+'_SolarReactivePowers.csv;\n'\
                                '  interval '+record_int+';\n'\
                                '}\n\n')
    
writefile.write('object group_recorder {\n'\
                '      group "groupid=Distribution_Line";\n'\
                '      property power_out; \n'\
                '      file ' +filename.replace('_mod.glm','')+'_DistLines.csv;\n'\
                '      interval 1800;\n'\
                '}\n\n')

writefile.write('object group_recorder {\n'\
                '      group "groupid=Distribution_Trans";\n'\
                '      property power_out; \n'\
                '      file ' +filename.replace('_mod.glm','')+'_DistTrans.csv;\n'\
                '      interval 1800;\n'\
                '}\n\n')

writefile.write('object group_recorder {\n'\
                '      group "groupid=tnode";\n'\
                '      property voltage_12;\n'\
                '      file '+filename.replace('_mod.glm','')+'_triplex_node.csv;\n'\
                '      interval 1800;\n'\
                 '}\n\n')

writefile.write('object group_recorder {\n'\
                '      group "groupid=tmeter";\n'\
                '      property voltage_12;\n'\
                '      file '+filename.replace('_mod.glm','')+'_triplex_meter.csv;\n'\
                '      interval 1800;\n'\
                 '}\n\n')

writefile.write('object group_recorder {\n'\
                '      group "groupid=node";\n'\
                '      property voltage_A;\n'\
                '      file '+filename.replace('_mod.glm','')+'_node_voltage_a.csv;\n'\
                '      interval 1800;\n'\
                 '}\n\n')

writefile.write('object group_recorder {\n'\
                '      group "groupid=node";\n'\
                '      property voltage_B;\n'\
                '      file '+filename.replace('_mod.glm','')+'_node_voltage_b.csv;\n'\
                '      interval 1800;\n'\
                 '}\n\n')

writefile.write('object group_recorder {\n'\
                '      group "groupid=node";\n'\
                '      property voltage_C;\n'\
                '      file '+filename.replace('_mod.glm','')+'_node_voltage_c.csv;\n'\
                '      interval 1800;\n'\
                 '}\n\n')



'''
# house load meter recorders
record_int = '60'
include_house_recorders = True
if include_house_recorders:
    for node in nodes:
        ndobj = node_objs[node]
        ndtype_match = re.search('object .*?\{',ndobj,re.DOTALL)
        if ndtype_match is not None:
            ndtype = ndtype_match.group().replace('object ','').strip(' \{')
            if ndtype == 'house':
                # generate name of recorder
                load_label = node.replace(feeder_name+'_','')
                # find the name of its meter (parent)
                parent_match = re.search('parent .*?;',ndobj,re.DOTALL)
                parent = parent_match.group().replace('parent ','').strip(';')
                # add a recorder
                writefile.write('object recorder {\n'\
                                '  name '+load_label+'_rec;\n'\
                                '  parent '+parent+';\n'\
                                '  property measured_real_power,measured_reactive_power;\n'\
                                '  file '+load_label+'_powers.csv;\n'\
                                '  interval '+record_int+';\n'\
                                '}\n\n')      
        
# der input power recorders
record_int = '60'
include_der_recorders = True
if include_der_recorders:
    for node in nodes:
        ndobj = node_objs[node]
        ndtype_match = re.search('object .*?\{',ndobj,re.DOTALL)
        if ndtype_match is not None:
            ndtype = ndtype_match.group().replace('object ','').strip(' \{')
            if ndtype == 'triplex_meter':
                inv_match = re.search('object inverter \{',ndobj,re.DOTALL)
                if inv_match is not None:
                    # generate name of recorder
                    inv_label = node.replace(feeder_name+'_','')
                    # find the name of its meter
                    name_match = re.search('name .*?;',ndobj,re.DOTALL)
                    name = name_match.group().replace('name ','').strip(';')
                    # add a recorder for metered powers
                    writefile.write('object recorder {\n'\
                                    '  name '+inv_label+'_rec;\n'\
                                    '  parent '+name+';\n'\
                                    '  property measured_real_power,measured_reactive_power;\n'\
                                    '  file '+inv_label+'_powers.csv;\n'\
                                    '  interval '+record_int+';\n'\
                                    '}\n\n')
                    # add a recorder for inverter DC input
                    writefile.write('object recorder {\n'\
                                    '  name '+inv_label+'_rec_Pin;\n'\
                                    '  parent '+node.replace('invm','inv')+';\n'\
                                    '  property P_In;\n'\
                                    '  file '+inv_label+'_Pin.csv;\n'\
                                    '  interval '+record_int+';\n'\
                                    '}\n\n')
'''
# close all files
readfile.close
node_data_file.close
branch_data_file.close
load_data_file.close
der_data_file.close
writefile.close