import os
import matlab.engine
import numpy as np
import datetime as dt
from shutil import copyfile
from odbAccess import *
from abaqusConstants import *
from operator import itemgetter

def takeFirst(elem):
    return elem[0]
def takeSecond(elem):
    return elem[1]
def takeThird(elem):
    return elem[2]

## Parameters
directory_matlab_script = r'./'
directory_current       = './'
name_new_odb            = 'new_183MS.odb'
name_template_odb       = 'raw_2x2.odb'
name_local_heat_step    = 'Step-heat'
name_time_log_file      = "postproc_combine_time_log.txt"
cue_local               = 'L'
cue_global              = 'G'
cue_heat_step           = 'heat'
number_of_frames        = 11
digits_of_time          = 9  

## TS: Start
srt_dt    = dt.datetime.now()
time_line = "Start:   " + str(srt_dt) + "\r"
time_file = open(name_time_log_file, "a+")
time_file.write(time_line)
time_file.close()
prv_dt    = dt.datetime.now()
print time_line
##

eng = matlab.engine.start_matlab()              # The matlab engine is used to run matlab functions    
eng.addpath(directory_current,nargout=0)    # Adding the custom function directory to the matlab engine

## TS: Matlab Engine End
cur_dt    = dt.datetime.now()
time_line = "MtlbEng: " + str(cur_dt - prv_dt) + "\r"
time_file = open(name_time_log_file, "a+")
time_file.write(time_line)
time_file.close()
prv_dt    = cur_dt
print time_line
##

if os.path.isfile(name_new_odb):     # Delete the previously created file.
    os.remove(name_new_odb)
    print('>>> Old odb removed.')
else:                                 # If no old file is found just skip and create a new one.
    print('>>> Created new ODB.')
copyfile(name_template_odb, name_new_odb)

## Create list of global and local files names
files=[]
for (dirpath, dirnames, filenames) in os.walk(directory_current):
    files.extend(filenames)
    break
files_glb = []
files_lcl = []
for cur_file in files:
    if cue_local in cur_file:
        files_lcl.append(cur_file)
    elif cue_global in cur_file:
        files_glb.append(cur_file)

## Start
odb_new = openOdb(path=name_new_odb,readOnly=False)         # New empty ODB where we write
ins_new = odb_new.rootAssembly.instances.items()[0][1]      # New instance
nodeLabel_new = tuple(range(1,ins_new.nodes.__len__()+1))   # A tuple contatining all node labels
                                                            # it will be used for assigning data to new ODB

layer_id = 0                                                # Init of layer index
local_id = 0                                                # Init of local index
##>>For each Gloabl File/Layer
for layer_id in range(files_glb.__len__()):
    odb_ref = openOdb(path=files_glb[layer_id])             # Open the ODB with simulation data
    ins_ref = odb_ref.rootAssembly.instances.items()[0][1]  # Assign refernce instance
    step_keys = odb_ref.steps.keys()                        # Step names in current layer
    segment_id = 0                                          # Init of segment index
    
    ##>>For each Local Simulation/Segment
    for segment_id in range(step_keys.__len__()):
        print ('>>> Started  '+step_keys[segment_id])
        
        ##>>Heated Local
        if cue_heat_step in step_keys[segment_id]:
            odb_lcl = openOdb(path=files_lcl[local_id],readOnly=False)  # Local model with correct data
            ins_lcl = odb_lcl.rootAssembly.instances.items()[0][1]      # Local instance
            
            x_min_lcl = ins_lcl.nodes[0].coordinates[0]                 # Top right corner
            x_max_lcl = ins_lcl.nodes[0].coordinates[0]                 #  and bottom left
            y_min_lcl = ins_lcl.nodes[0].coordinates[1]                 #  corner of the 
            y_max_lcl = ins_lcl.nodes[0].coordinates[1]                 #  local model.
            
            for node in ins_lcl.nodes:          # Searches through all nodes to find the corners
                cur_x = node.coordinates[0]
                cur_y = node.coordinates[1]
                if cur_x < x_min_lcl:
                    x_min_lcl = cur_x
                if cur_x > x_max_lcl:
                    x_max_lcl = cur_x
                if cur_y < y_min_lcl:
                    y_min_lcl = cur_y
                if cur_y > y_max_lcl:
                    y_max_lcl = cur_y
            
            ## Find part of new model to swap with previous ones
            labels_new_swap_lcl = []    # List of node LABELS coming from the local  model in the new ODB
            labels_new_swap_glb = []    # List of node LABELS coming from the global model in the new ODB
            x_new_swap_lcl = []         # X Vector for local  interpolation
            y_new_swap_lcl = []         # Y Vector for local  interpolation
            x_new_swap_glb = []         # X Vector for global interpolation
            y_new_swap_glb = []         # Y Vector for global interpolation
            for node in ins_new.nodes:  # Filling up above vectors
                cur_x = node.coordinates[0]
                cur_y = node.coordinates[1]
                if     (cur_x > x_min_lcl 
                    and cur_x < x_max_lcl
                    and cur_y > y_min_lcl
                    and cur_y < y_max_lcl):
                    labels_new_swap_lcl.append(node.label)
                    x_new_swap_lcl.append(cur_x.item())
                    y_new_swap_lcl.append(cur_y.item())
                else:
                    labels_new_swap_glb.append(node.label)
                    x_new_swap_glb.append(cur_x.item())
                    y_new_swap_glb.append(cur_y.item())
                    
            ## Local X/Y vectors for interapolation
            x_lcl = []
            y_lcl = []
            for node in ins_lcl.nodes:
                x_lcl.append(node.coordinates[0].item())
                y_lcl.append(node.coordinates[1].item())
                
            ## Global X/Y vectors for interapolation
            x_ref = []
            y_ref = []
            for node in ins_ref.nodes:
                x_ref.append(node.coordinates[0].item())
                y_ref.append(node.coordinates[1].item())

            ## Creating the new step and assigning the corresponding ones
            cur_ref_step = odb_ref.steps[step_keys[segment_id]]
            cur_lcl_step = odb_lcl.steps[name_local_heat_step]
            step_new = odb_new.Step(   name=step_keys[segment_id], description='', domain=TIME, timePeriod=cur_ref_step.timePeriod, totalTime=cur_ref_step.totalTime) # Creating corresponding step in new ODB

            ## Arbitrary frame times in the new odb
            time_frames = np.linspace(0., cur_ref_step.timePeriod, num=number_of_frames)

            prev_lcl_frame_id = 0
            next_lcl_frame_id = 0
            prev_ref_frame_id = 0
            next_ref_frame_id = 0
            
            ##>>Each step frame
            for frame_id in range(time_frames.__len__()):
                cur_new_time = time_frames[frame_id].item()
                ## Where new frame lies with respect to local frames
                for lcl_frame_id in range(prev_lcl_frame_id,cur_lcl_step.frames.__len__()):
                    if cur_lcl_step.frames[lcl_frame_id].frameValue > cur_new_time:
                        next_lcl_frame_id = lcl_frame_id
                        break
                    prev_lcl_frame_id = lcl_frame_id
                prev_lcl_frame = cur_lcl_step.frames[prev_lcl_frame_id] 
                next_lcl_frame = cur_lcl_step.frames[next_lcl_frame_id]   
                prev_lcl_nt = prev_lcl_frame.fieldOutputs['NT11'].values
                next_lcl_nt = next_lcl_frame.fieldOutputs['NT11'].values
                prev_lcl_time = prev_lcl_frame.frameValue
                next_lcl_time = next_lcl_frame.frameValue
                
                ## Where new frame lies with respect to reference frames
                for ref_frame_id in range(prev_ref_frame_id,cur_ref_step.frames.__len__()):
                    if cur_ref_step.frames[ref_frame_id].frameValue > cur_new_time:
                        next_ref_frame_id = ref_frame_id
                        break
                    prev_ref_frame_id = ref_frame_id
                prev_ref_frame = cur_ref_step.frames[prev_ref_frame_id] 
                next_ref_frame = cur_ref_step.frames[next_ref_frame_id]   
                prev_ref_nt = prev_ref_frame.fieldOutputs['NT11'].values
                next_ref_nt = next_ref_frame.fieldOutputs['NT11'].values
                prev_ref_time = prev_ref_frame.frameValue
                next_ref_time = next_ref_frame.frameValue

                
                ## Interpolating the temperatures
                T_lcl = []  # Local  temperature vector for interapolation
                T_ref = []  # Global temperature vector for interapolation
                for node_id in range(prev_lcl_nt.__len__()):
                    T_lcl_prev = prev_lcl_nt[node_id].data
                    T_lcl_next = next_lcl_nt[node_id].data
                    if prev_lcl_frame_id == next_lcl_frame_id:
                        T_lcl_cur = T_lcl_prev
                    else:
                        T_lcl_cur = T_lcl_prev + (T_lcl_next-T_lcl_prev)/(next_lcl_time-prev_lcl_time)*(cur_new_time-prev_lcl_time)
                    T_lcl.append(T_lcl_cur)
                for node_id in range(prev_ref_nt.__len__()):
                    T_ref_prev = prev_ref_nt[node_id].data
                    T_ref_next = next_ref_nt[node_id].data
                    if prev_ref_frame_id == next_ref_frame_id:
                        T_ref_cur = T_ref_prev
                    else:
                        T_ref_cur = T_ref_prev + (T_ref_next-T_ref_prev)/(next_ref_time-prev_ref_time)*(cur_new_time-prev_ref_time)
                    T_ref.append(T_ref_cur)
                    
                ## Sorting the lcl data for easier interpolation
                lcl_pack = []
                for id in range(T_lcl.__len__()):
                    cur_row = [round(x_lcl[id],9),round(y_lcl[id],9),round(T_lcl[id],9)]
                    lcl_pack.append(cur_row)
                lcl_pack.sort(key=takeSecond)
                lcl_pack.sort(key=takeFirst)
                lcl_pack = np.transpose(lcl_pack)
                
                x_lcl_sort = lcl_pack[0].tolist()
                y_lcl_sort = lcl_pack[1].tolist()
                T_lcl_sort = lcl_pack[2].tolist()
                
                ## Making a vector out of x
                zeroth_x = x_lcl_sort[0]
                step_counter = 1
                for indx in range(1,x_lcl_sort.__len__()):
                    if x_lcl_sort[indx] == zeroth_x:
                        step_counter = step_counter+1
                    else:
                        break
                step_numbers = range(0,x_lcl_sort.__len__(),step_counter)
                vector_x_length = step_numbers.__len__()

                ## Making a vector out of y
                zeroth_y = y_lcl_sort[0]
                teeth_counter = 1
                for indx in range(1,y_lcl_sort.__len__()):
                    if y_lcl_sort[indx] != zeroth_y:
                        teeth_counter = teeth_counter+1
                    else:
                        break
                vector_y_length = teeth_counter
                
                
                T_swap_lcl = eng.interpolate_vectors_sort(x_lcl_sort,y_lcl_sort,T_lcl_sort,               # Where the intrapolation magic happens with Matlab
                                                     x_new_swap_lcl,y_new_swap_lcl,vector_y_length,vector_x_length)   
                T_swap_glb = eng.interpolate_vectors(x_ref,y_ref,T_ref,               # Where the intrapolation magic happens with Matlab
                                                     x_new_swap_glb,y_new_swap_glb) 
                T_swap_lcl = T_swap_lcl[0]                                            # Matlab returns the 2D single element array  
                T_swap_glb = T_swap_glb[0]                                            # Matlab returns the 2D single element array 
                
                ## Assining a temperature to each node in new ODB
                temp_from_local = []
                temp_from_globl = []
                for i in range(labels_new_swap_lcl.__len__()):
                    temp_from_local.append((T_swap_lcl[i],labels_new_swap_lcl[i]))
                for i in range(labels_new_swap_glb.__len__()):
                    temp_from_globl.append((T_swap_glb[i],labels_new_swap_glb[i]))
                temp_messy = temp_from_local+temp_from_globl
                temp_sorted = sorted(temp_messy, key=itemgetter(1))
                new_temp_list = []
                for cur_tup in temp_sorted:
                    new_temp_list.append((cur_tup[0],))
                tempData = tuple(new_temp_list)
                
                ## Adding the data to new ODB
                frm_new = step_new.Frame(incrementNumber = frame_id,
                                      frameValue      = cur_new_time,
                                      description     = 'Increment = '+str(frame_id)+' Time = '+str(np.around(cur_new_time, decimals=digits_of_time))) # Create the new frame
                tField  = frm_new.FieldOutput(name        = 'NT11',
                                              description = 'Temperatures',
                                              type        =  SCALAR)         # Create new temperature field
                tField.addData(position = NODAL,
                               instance = ins_new,
                               labels   = nodeLabel_new,
                               data     = tempData)       # Add the temperature tuple
                step_new.setDefaultField(tField)          # This makes ODB show the data 
                
            odb_lcl.close()
            local_id += 1
        
        ##>>Cool down
        else:
            ## Find part of new model to swap with previous one
            labels_new_swap_glb = []    # List of node LABELS coming from the global model in the new ODB
            x_new_swap_glb = []         # X Vector for global interpolation
            y_new_swap_glb = []         # Y Vector for global interpolation
            for node in ins_new.nodes:  # Filling up above vectors
                labels_new_swap_glb.append(node.label)
                x_new_swap_glb.append(node.coordinates[0].item())
                y_new_swap_glb.append(node.coordinates[1].item())
                    
            ## Global X/Y vectors for interapolation
            x_ref = []
            y_ref = []
            for node in ins_ref.nodes:
                x_ref.append(node.coordinates[0].item())
                y_ref.append(node.coordinates[1].item())

            ## A single step case example
            cur_ref_step = odb_ref.steps[step_keys[segment_id]]
            step_new = odb_new.Step(   name=step_keys[segment_id], description='', domain=TIME, timePeriod=cur_ref_step.timePeriod, totalTime=cur_ref_step.totalTime) # Creating corresponding step in new ODB
            
            ## Arbitrary frame times in the new odb
            time_frames = np.logspace(-4.6, np.log10(cur_ref_step.timePeriod), num=np.floor(number_of_frames*2)).tolist()
            time_frames.insert(0,0)

            prev_ref_frame_id = 0
            next_ref_frame_id = 0
            
            ##>>Each step frame
            for frame_id in range(time_frames.__len__()):
                cur_new_time = time_frames[frame_id]
                ## Where new frame lies with respect to reference frames
                for ref_frame_id in range(prev_ref_frame_id,cur_ref_step.frames.__len__()):
                    if cur_ref_step.frames[ref_frame_id].frameValue > cur_new_time:
                        next_ref_frame_id = ref_frame_id
                        break
                    prev_ref_frame_id = ref_frame_id
                prev_ref_frame = cur_ref_step.frames[prev_ref_frame_id] 
                next_ref_frame = cur_ref_step.frames[next_ref_frame_id]   
                prev_ref_nt = prev_ref_frame.fieldOutputs['NT11'].values
                next_ref_nt = next_ref_frame.fieldOutputs['NT11'].values
                prev_ref_time = prev_ref_frame.frameValue
                next_ref_time = next_ref_frame.frameValue
                
                ## Interpolating the temperatures
                T_ref = []  # Global temperature vector for interapolation
                for node_id in range(prev_ref_nt.__len__()):
                    T_ref_prev = prev_ref_nt[node_id].data
                    T_ref_next = next_ref_nt[node_id].data
                    if prev_ref_frame_id == next_ref_frame_id:
                        T_ref_cur = T_ref_prev
                    else:
                        T_ref_cur = T_ref_prev + (T_ref_next-T_ref_prev)/(next_ref_time-prev_ref_time)*(cur_new_time-prev_ref_time)
                    T_ref.append(T_ref_cur)
                    
                ## Sorting global data for easier interpolation
                ref_pack = []
                for id in range(T_ref.__len__()):
                    cur_row = [x_ref[id],y_ref[id],T_ref[id]]
                    ref_pack.append(cur_row)
                ref_pack.sort(key=takeSecond)
                ref_pack.sort(key=takeFirst)
                ref_pack = np.transpose(ref_pack)
                
                T_swap_glb = eng.interpolate_vectors(x_ref,y_ref,T_ref,               # Where the intrapolation magic happens with Matlab
                                                     x_new_swap_glb,y_new_swap_glb)   
                T_swap_glb = T_swap_glb[0]                                            # Matlab returns the 2D single element array 
                
                ## Assining a temperature to each node in new ODB
                new_temp_list = []
                for i in range(labels_new_swap_glb.__len__()):
                    new_temp_list.append((T_swap_glb[i],))
                tempData = tuple(new_temp_list)
                
                ## Adding the data to new ODB
                frm_new = step_new.Frame(incrementNumber = frame_id,
                                      frameValue      = cur_new_time,
                                      description     = 'Increment = '+str(frame_id)+' Time = '+str(np.around(cur_new_time, decimals=digits_of_time))) # Create the new frame
                tField  = frm_new.FieldOutput(name        = 'NT11',
                                              description = 'Temperatures',
                                              type        =  SCALAR)         # Create new temperature field
                tField.addData(position = NODAL,
                               instance = ins_new,
                               labels   = nodeLabel_new,
                               data     = tempData)       # Add the temperature tuple
                step_new.setDefaultField(tField)             # This makes ODB show the data        
        odb_new.save()      # For each step the new ODB should be saved

        ## TS: End of Swapping data for a step
        cur_dt    = dt.datetime.now()
        time_line = "    SwapEnd: " + str(cur_dt - prv_dt) + "\r"
        time_file = open(name_time_log_file, "a+")
        time_file.write(time_line)
        time_file.close()
        prv_dt    = cur_dt
        print time_line
        ##

        ## TS: End of Swapping data for a step
        end_dt    = dt.datetime.now()
        time_line = "    TtlTime: " + str(end_dt - srt_dt) + "\r"
        time_file = open(name_time_log_file, "a+")
        time_file.write(time_line)
        time_file.close()
        print time_line
        print ('>>> Finished '+step_keys[segment_id])
        ##
    odb_ref.close()
        
odb_new.close()    



print ('>>> Finished successfully.')