import code_ndprocw
import datetime as dt

global_file = '183GC'   # File name of global input
global_model = '180G'   # The name of sub-files for steps and material
local_file = '180L'     # File name of local  input
fortran_file = '180'    # File name of common subroutine

## Parameters
time_file_directory = "0_time_log.txt"

LOCALS = 10              # number of local models in a layer
LAYERS = 66             # number of total layers in global model
GLOBAL_LENGTH = 2E-3    # print length in global model
THICKNESS = 30E-6       # layer thickness
VELOCITY = 800E-3       # scan speed
COOL_TIME = 1           # duration of cool down step
LOCAL_LENGTH = GLOBAL_LENGTH / LOCALS       # print length in  local model
HEAT_TIME = GLOBAL_LENGTH / VELOCITY        # duration of heating step
TOTAL_LAYER_TIME = COOL_TIME + HEAT_TIME    # total time it takes to print a layer

global_input = code_ndprocw.Input(global_file)
global_fort = code_ndprocw.Fort(fortran_file)
global_fort.write_file('all', fortran_file)

## Start time stamp
str_dt = dt.datetime.now()
time_line = "Start " + str(str_dt) + "\rGlobal: <" + global_file + ">   Local: <" + local_file + ">\r"
time_file = open(time_file_directory, "a+")
time_file.write(time_line)
time_file.close()
prv_dt = str_dt
##

for layer_id in range(LAYERS):

    # Create and write to file the layer global model
    global_input.create_global_layer(global_model, layer_id, LOCALS)

    # Run the global model for each layer
    code_ndprocw.RunGlobals(global_file, fortran_file+'_0all', layer_id)

    ## TS
    cur_dt = dt.datetime.now()  # Timestamp
    time_line = "  Global_" + str(layer_id).zfill(4) + " " + str(cur_dt - prv_dt) + "\r"
    time_file = open(time_file_directory, "a+")
    time_file.write(time_line)
    time_file.close()
    prv_dt = cur_dt
    ##

    # Laser movement direction
    d_x = (-1) ** layer_id
    for segment_id in range(LOCALS):
        # number of current local model
        local_id = segment_id + layer_id * LOCALS

        # read the input file
        local_input = code_ndprocw.Input(local_file)

        # move the nodes
        x_shift = 0  # amount of shift in the x direction
        y_shift = 0  # amount of shift in the y direction
        if d_x > 0:
            x_shift = LOCAL_LENGTH * segment_id
        else:
            x_shift = GLOBAL_LENGTH - (LOCAL_LENGTH * segment_id)
        y_shift = THICKNESS * layer_id
        local_input.move_nodes(x_shift, y_shift, d_x)

        # assign convection direction
        local_input.set_surface_direction(d_x)

        # assign T0 model
        local_input.set_initial_temp(local_file, global_file, local_id, segment_id, layer_id, LOCALS)

        # assign submodel step number
        local_input.set_submodel_step(layer_id * (LOCALS + 1) + segment_id + 1)

        # write the input file
        local_input.write_file(local_id)

        # set the time shift in the fortran file#
        local_fort = code_ndprocw.Fort(fortran_file)
        local_fort.shift_time(layer_id * TOTAL_LAYER_TIME + segment_id * LOCAL_LENGTH / VELOCITY)
        local_fort.set_step(layer_id * (LOCALS + 1) + segment_id + 1)

        # write the fortran file
        local_fort.write_file(local_id, local_file)

        # run the simulation
        code_ndprocw.RunLocal(local_file + '_' + str(local_id).zfill(4), global_file, layer_id)
        
        ## TS
        cur_dt = dt.datetime.now()
        time_line = "    Local_" + str(local_id).zfill(4) + " " + str(cur_dt - prv_dt) + "\r"
        time_file = open(time_file_directory, "a+")
        time_file.write(time_line)
        time_file.close()
        prv_dt = cur_dt
        ##

## TS:End time stamp
end_dt = dt.datetime.now()
time_line = "End " + str(end_dt) + "\rDuration " + str(end_dt - str_dt) + "\r\n"
time_file = open(time_file_directory, "a+")
time_file.write(time_line)
time_file.close()
##
