class Input:
    def __init__(self, file_path):
        self.file_name = file_path

        f = open('0_'+file_path+'.inp', "r")
        self.contents = f.readlines()
        f.close()

        i = 1
        self.line_node_start    = 0
        self.line_element_start = 0
        self.line_element_end   = 0
        for each_line in self.contents:
            if each_line.split(',')[0] == '*Node\n':
                self.line_node_start = i
            elif each_line.split(',')[0] == '*Element':
                self.line_element_start = i
            elif each_line.split(',')[0] == '*Nset':
                self.line_element_end = i-2
                break
            i += 1
        self.node_length = self.line_element_start - self.line_node_start - 1
        self.element_length = self.line_element_end - self.line_element_start + 1

        self.x = []
        self.y = []
        for i in range(self.node_length):
            self.x.append(round(float(self.contents[self.line_node_start + i].split(',')[1]), 6))
            self.y.append(round(float(self.contents[self.line_node_start + i].split(',')[2]), 6))

        self.e = []
        i = 0
        while True:
            element_nodes = self.contents[self.line_element_start + i].split(',')
            try:
                int(element_nodes[0])
            except ValueError:
                if element_nodes[0] == '*Element':
                    pass
                else:
                    break
            else:
                node_list = []
                for node in element_nodes[1:]:
                    node_list.append(int(node))
                self.e.append(node_list)
            i += 1

        for i in reversed(range(self.node_length)):
            rounded_node = str(i + 1) + ',' + str(self.x[i]) + ',' + str(self.y[i]) + '\n'
            self.contents[self.line_node_start + i] = rounded_node

    def move_nodes(self, new_x, new_y, direction):
        for i in reversed(range(self.node_length)):
            self.x[i] = self.x[i] * direction
            self.x[i] = round(self.x[i]+new_x,6)
            self.y[i] = round(self.y[i]+new_y,6)
            moved_node = str(i + 1) + ',' + str(self.x[i]) + ',' + str(self.y[i]) + '\n'
            self.contents[self.line_node_start + i] = moved_node
        if direction == -1 :
            for i in reversed(range(self.element_length)):
                self.e[i].reverse()
                new_element = str(i+1)+','
                for element_node in self.e[i]:
                    new_element += str(element_node)+','
                self.contents[self.line_element_start + i] = new_element[:-1] + '\n'

    def set_initial_temp(self, local_name, global_name, local_id, segment_id, layer_id, n_locals):
        line_initial_temp = self.contents.index(
            'FLAG_INITIAL_CONDITIONS\n')
        line_initial_fvd1 = line_initial_temp+1

        if segment_id == 0:
            if layer_id == 0:
                new_line_temp = '*Initial Conditions, type=TEMPERATURE\nPart-local-1.Set-all, 25.\n'
                new_line_fvd1 = ''
            else:
                new_line_temp = '*Initial Conditions, type=TEMPERATURE, file=run_' + global_name + '_' + str(
					layer_id - 1).zfill(4) + '.odb, step=' + str(n_locals + 1) + ', interpolate\n'
                new_line_fvd1 = '*Initial Conditions, type=FIELD, variable=1, file=run_' + local_name + '_' + str(
                    local_id - 1).zfill(4) + '.odb, output variable=NT, step=2, interpolate\n'
        else:
            new_line_temp = '*Initial Conditions, type=TEMPERATURE, file=run_' + local_name + '_' + str(
                local_id-1).zfill(4) + '.odb, step=1, interpolate\n'
            new_line_fvd1 = '*Initial Conditions, type=FIELD, variable=1, file=run_' + local_name + '_' + str(
                local_id-1).zfill(4) + '.odb, output variable=NT, step=2, interpolate\n'

        self.contents[line_initial_temp] = new_line_temp
        self.contents[line_initial_fvd1] = new_line_fvd1

    def set_submodel_step(self, step):
        line_initial_temp = self.contents.index(
            '*Boundary, submodel, step=1\n')
        self.contents[
            line_initial_temp] = '*Boundary, submodel, step=' + str(step) + '\n'

    def set_surface_direction(self, direction):
        if direction < 0:
            line_surface = self.contents.index('Part-local-1.Set-all,F1NU\n')
            new_line_surface = 'Part-local-1.Set-all,F3NU\n'
            self.contents[line_surface] = new_line_surface

    def create_global_layer(self,global_model, layer_id, n_locals):
        if layer_id == 0:   # First layer
            line_steps = self.contents.index('STEP_DEFINITION_FLAG\n')  # Line index of steps
            # Heating Steps
            for segment_id in range(n_locals):
                local_id = segment_id + layer_id * n_locals     # Same as segment_id here
                if local_id == 0:   # The very first local model
                    first_heat = '*Step, name=Step-heat-' + str(
                        local_id) + ', nlgeom=NO, inc=100000\n*INCLUDE,input=' + global_model + '_h0.inp\n'
                    self.contents[line_steps] = first_heat
                else:
                    new_heat = '*Step, name=Step-heat-' + str(
                        local_id) + ', nlgeom=NO, inc=100000\n*INCLUDE,input=' + global_model + '_h.inp\n'
                    self.contents.insert(line_steps + segment_id + layer_id * (n_locals + 1), new_heat)
            # Cooling Step
            new_cool = '*Step, name=Step-cool-' + str(
                layer_id) + ', nlgeom=NO, inc=100000\n*INCLUDE,input=' + global_model + '_c.inp\n'
            self.contents.insert(line_steps + (layer_id + 1) * (n_locals + 1) - 1, new_cool)
            # Writing into file
            self.write_file(layer_id)
        else:               # Subsequent layers (restart)
            temp_contents = []
            # Heating Steps
            for segment_id in range(n_locals):
                local_id = segment_id + layer_id * n_locals
                new_heat = '*Step, name=Step-heat-' + str(
                    local_id) + ', nlgeom=NO, inc=100000\n*INCLUDE,input=' + global_model + '_h.inp\n'
                temp_contents.insert(segment_id + layer_id * (n_locals + 1), new_heat)
            # Cooling Steps
            new_cool = '*Step, name=Step-cool-' + str(
                layer_id) + ', nlgeom=NO, inc=100000\n*INCLUDE,input=' + global_model + '_c.inp\n'
            temp_contents.insert(n_locals, new_cool)
            # Writing into file
            file_new = open(self.file_name + '_' + str(layer_id).zfill(4) + '.inp', "w+")
            file_new.write("*Heading\n*Restart, read\n")
            for i in range(n_locals + 1):
                file_new.write(temp_contents[i])
            file_new.close()

    def write_file(self, index):
        file_new = open(self.file_name + '_' + str(index).zfill(4) + '.inp', "w+")
        for line in self.contents:
            file_new.write(line)
        file_new.close()


class Fort:
    def __init__(self,file_path):
        f = open(file_path + '.f', "r")
        self.contents = f.readlines()
        f.close()

    def write_file(self, index, new_name):
        file_new = open(new_name + '_' + str(index).zfill(4) + '.f', "w+")
        for line in self.contents:
            file_new.write(line)
        file_new.close()

    def shift_time(self, time):
        line_t0 = self.contents.index('      REAL*8, PARAMETER :: TIME_SHIFT     = 0.D0\n')
        if time == 0:
            time_string = '0.D0'
        else:
            time_string = str(round(time,8)) + 'D0'
        self.contents[line_t0] =      '      REAL*8, PARAMETER :: TIME_SHIFT     = ' + time_string + '\n'

    def set_step(self,index):
        line_it = self.contents.index('      REAL*8, PARAMETER :: STEP           = 0.D0\n')
        self.contents[line_it] =      '      REAL*8, PARAMETER :: STEP           = ' + str(index) + '.D0\n'


class RunLocal:
    def __init__(self,input_file,global_odb,layer):
        cmd_dir = 'cd simulation\n'
        cmd_frt = 'ifortvars intel64\r\n'
        cmd_job = 'abaqus job=run_'+input_file+' user='+input_file+' input='+input_file+' globalmodel=run_'+global_odb+'_'+str(layer).zfill(4)+' cpus=8 interactive ask_delete=OFF\r\n'
        cmd = cmd_dir + ';' + cmd_frt + ';' + cmd_job

        import subprocess
        process = subprocess.Popen('cmd.exe', stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=None, shell=False)
        out = process.communicate(cmd.encode('utf-8', 'ignore'))[0]
        print(out.decode('utf-8', 'ignore'))


class RunGlobals:
    def __init__(self,global_file,fort_file,layer):
        input_file = global_file+'_'+str(layer).zfill(4)
        old_file = global_file+'_'+str(layer-1).zfill(4)

        cmd_dir = 'cd simulation\n'
        cmd_frt = 'ifortvars intel64\r\n'
        if layer == 0:
            cmd_job = 'abaqus job=run_' + input_file + ' user=' + fort_file + ' input=' + input_file + ' cpus=8 interactive ask_delete=OFF\r\n'
        else:
            cmd_job = 'abaqus job=run_' + input_file + ' oldjob=run_' + old_file + ' user=' + fort_file + ' input=' + input_file + ' cpus=8 interactive ask_delete=OFF\r\n'
        cmd = cmd_dir + ';' + cmd_frt + ';' + cmd_job

        import subprocess
        process = subprocess.Popen('cmd.exe', stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=None, shell=False)
        out = process.communicate(cmd.encode('utf-8', 'ignore'))[0]
        print(out.decode('utf-8', 'ignore'))
