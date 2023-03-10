# -*- coding: utf-8 -*-
"""
Created on Tue Jun 21 10:00:43 2022

@author: seragela
"""
import yaml, os
import numpy as np
import matplotlib.pyplot as plt
from ROSCO_toolbox import turbine as ROSCO_turbine
from ROSCO_toolbox import controller as ROSCO_controller
from ROSCO_toolbox.utilities import write_rotor_performance
from ROSCO_toolbox.inputs.validation import load_rosco_yaml
from ROSCO_toolbox.utilities import write_DISCON

def tune_ROSCO(yaml_file_name, ServoData_folder = 'ServoData', Kp_float = 0):
    """ Generates DISCON.IN input file for the ROSCO controller
    Fast_reader.py has to be modified to the correct OpenFAST version"""

    inps = load_rosco_yaml(yaml_file_name)
    path_params = inps['path_params']
    turbine_params = inps['turbine_params']
    controller_params = inps['controller_params']
    turbine = ROSCO_turbine.Turbine(turbine_params)
    # Generate performance file if it doesn't exist
    if (not os.path.exists(path_params['rotor_performance_filename'])):
        turbine.load_from_fast(
            path_params['FAST_InputFile'],
            path_params['FAST_directory'],
            dev_branch=True,
            rot_source='cc-blade',
            txt_filename=None)
        write_rotor_performance(turbine,path_params['rotor_performance_filename'])
    else:
        turbine.load_from_fast(
        path_params['FAST_InputFile'],
        path_params['FAST_directory'],
        dev_branch=True,
        rot_source='txt',txt_filename=path_params['rotor_performance_filename'])

    # Tune controller
    controller = ROSCO_controller.Controller(controller_params)
    controller.tune_controller(turbine)

    # Set floating feedback gain if given
    if Kp_float != 0:
        controller.Kp_float = Kp_float

    fst_root = path_params['FAST_InputFile'].split('.')[0]

    # Write DISCON.IN file
    write_DISCON(turbine,controller,param_file = fst_root + '_DISCON.IN', txt_filename = path_params['rotor_performance_filename'])

    return turbine, controller


def write_yaml(fileName):
    """ Sets control parameters dictionaries and writes the yaml parameters file to be used as input to the GetDISCON function
		Defaults and updated documation of parameters can be found here: https://rosco.readthedocs.io/en/latest/source/toolbox_input.html
	    
        These parameters are for the 10 MW OO floating turbine. 
        
        Some sources to this input file: 
		IEA 10 MW reference monopile: https://github.com/IEAWindTask37/IEA-10.0-198-RWT, https://windio.readthedocs.io/en/latest/source/control.html#control
		Note! The IEA 10 MW monopile uses a direct drive. See table 9 in this document for other changes: https://www.nrel.gov/docs/fy19osti/73492.pdf
	
	"""

    path_params = {'FAST_InputFile': fileName,                 # Name of *.fst file
                   'FAST_directory': '..',                            # Main OpenFAST model directory, where the *.fst lives
                   'rotor_performance_filename':  'Cp_Ct_Cq_10MW.txt' # Filename for rotor performance text file (if it has been generated by ccblade already)
                   }

    turbine_params = {'rotor_inertia':      156243120,                         # Rotor inertia [kg m^2], {Available in Elastodyn .sum file}
                      'rated_rotor_speed':  9.60*2*np.pi/60,                   # Rated rotor speed [rad/s]
                      'v_min':              4.0,                               # Cut-in wind speed [m/s]
                      'v_rated':            11.4,                              # Rated wind speed [m/s]
                      'v_max':              25.0,                              # Cut-out wind speed [m/s]
                      'max_pitch_rate':     10.0*np.pi/180,                    # Maximum blade pitch rate [rad/s] -- Taken from IEA 10 MW reference monopile
                      'max_torque_rate':    1.5e+6,							   # Maximum torque rate [Nm/s], {~1/4 VS_RtTq/s} -- Taken from IEA 10 MW reference monopile
                      'rated_power':        10000000.0,                        # Rated Power [W]
                      'bld_edgewise_freq':  0.93*2*np.pi,                      # Blade edgewise first natural frequency [rad/s] --Taken from DTU 10 MW report
                      'bld_flapwise_freq':  0.61*2*np.pi,                      # Blade flapwise first natural frequency [rad/s] --Taken from DTU 10 MW report
                      'TSR_operational':    7.5						       	   # Taken from DTU 10 MW report. Note that the IEA 10 MW reference monopile uses a different radius - do not use TSR from this model
                      }

    controller_params = {  # Controller flags
                          'LoggingLevel':       1,                     # {0: write no debug files, 1: write standard output .dbg-file, 2: write standard output .dbg-file and complete avrSWAP-array .dbg2-file
                          'F_LPFType':          2,                     # {1: first-order low-pass filter, 2: second-order low-pass filter}, [rad/s] (currently filters generator speed and pitch control signals)
                          'F_NotchType':        0,                     # Notch on the measured generator speed and/or tower fore-aft motion (for floating) {0- disable, 1- generator speed, 2- tower-top fore- aft motion, 3- generator speed and tower-top fore-aft motion}
                          'IPC_ControlMode':    0,                     # Turn Individual Pitch Control (IPC) for fatigue load reductions (pitch contribution) {0: off, 1: 1P reductions, 2: 1P+2P reductions}
                          'VS_ControlMode':     2,                     # Generator torque control mode in above rated conditions {0- constant torque, 1- constant power, 2- TSR tracking PI control with constant torque, 3- TSR tracking with constant power}
                          'PC_ControlMode':     1,                     # Blade pitch control mode {0: No pitch, fix to fine pitch, 1: active PI blade pitch control}
                          'Y_ControlMode':      0,                     # Yaw control mode {0: no yaw control, 1: yaw rate control, 2: yaw-by-IPC}
                          'SS_Mode':            1,                     # Setpoint Smoother mode {0: no setpoint smoothing, 1: introduce setpoint smoothing}
                          'WE_Mode':            2,                     # Wind speed estimator mode {0: One-second low pass filtered hub height wind speed, 1: Immersion and Invariance Estimator (Ortega et al.)}. Default = 2
                          'PS_Mode':            3,                     # Pitch saturation mode {0: no pitch saturation, 1: peak shaving, 2: Cp-maximizing pitch saturation, 3: peak shaving and Cp-maximizing pitch saturation}
                          'SD_Mode':            0,                     # Shutdown mode {0: no shutdown procedure, 1: pitch to max pitch at shutdown}
                          'Fl_Mode':            0,                     # Floating specific feedback mode {0- no nacelle velocity feedback, 1 - nacelle velocity feedback, 2 - nacelle pitching acceleration feedback})
                          'Flp_Mode':           0,                     # Flap control mode {0: no flap control, 1: steady state flap angle, 2: Proportional flap control}
                          # Controller parameters
                          # 'U_pc':               10,
                          'zeta_pc':            1,                     # Pitch controller desired damping ratio [-]  -- Taken from the IEA reference monopile https://windio.readthedocs.io/en/latest/source/control.html#control
                          'omega_pc':           0.2,                   # Pitch controller desired natural frequency [rad/s] -- Taken from the IEA reference monopile https://windio.readthedocs.io/en/latest/source/control.html#control
                          'zeta_vs':            1.0,                   # Torque controller desired damping ratio [-] -- Taken from the IEA reference monopile https://windio.readthedocs.io/en/latest/source/control.html#control
                          'omega_vs':           0.2,                   # Torque controller desired natural frequency [rad/s] -- Taken from the IEA reference monopile https://windio.readthedocs.io/en/latest/source/control.html#control
                          # Optional - these can be defined, but do not need to be
						  # 'interp_type':        'sigma',
                          # 'max_pitch':          None,                  # Maximum pitch angle [rad], {default = 90 degrees}
                          # 'min_pitch':          None,                  # Minimum pitch angle [rad], {default = 0 degrees}
                          'vs_minspd':          0.732,                  # Minimum rotor speed [rad/s], {default = 0 rad/s} -- Taken from the IEA reference monopile https://windio.readthedocs.io/en/latest/source/control.html#control
                          # 'ss_cornerfreq':      None,                  # First order low-pass filter cornering frequency for setpoint smoother [rad/s]
                          'ss_vsgain':          1,                      # Torque controller setpoint smoother gain bias percentage [%, <= 1 ], {default = 100%} -- Taken from the IEA reference monopile https://windio.readthedocs.io/en/latest/source/control.html#control
                          'ss_pcgain':          0.001,                  # Pitch controller setpoint smoother gain bias percentage  [%, <= 1 ], {default = 0.1%}
                          'ps_percent':         0.8,                    # Percent peak shaving  [%, <= 1 ], {default = 80%}
                          # 'sd_maxpit':          None,                  # Maximum blade pitch angle to initiate shutdown [rad], {default = 40 deg}
                          # 'WS_GS_n':            None,
                          # 'PC_GS_n':            None,
                          # 'IPC_Kp1p':           None,
                          'IPC_Ki1p':           1.0e+5, 				# Integral gain for IPC, 1P [s], Default = 0.0
                          # 'IPC_Kp2p':           None,
                          # 'IPC_Ki2p':           None,
                          # 'sd_cornerfreq':      None,                  # Cutoff Frequency for first order low-pass filter for blade pitch angle [rad/s], {default = 0.41888 ~ time constant of 15s}
                          # 'flp_maxpit':         None,                   # Maximum (and minimum) flap pitch angle [rad]
                          #'twr_freq':  0.579*2*np.pi,                    # for semi only! -- Taken from the semi-flexible model in "State-of-the-art model for the LIFES50+ OO-Star Wind Floater Semi 10MW floating windturbine"
                          #'ptfm_freq': 0.032*2*np.pi                    # Platform first fore-aft natural frequency [rad/s]. Required for floating wind turbine control. -- Taken as platform pitch freq. from "D4.2 Public Definition of the Two LIFES50+ 10MW Floater Concepts"
                          } 
    # Write .yaml file
    fst_root = path_params['FAST_InputFile'].split('.')[0]
    yaml_dict = {'path_params':path_params, 'turbine_params':turbine_params,'controller_params':controller_params}
    yaml_file_name = fst_root + '.yaml'
    print(yaml_file_name)
    with open(yaml_file_name, 'w') as file:
        yaml.dump(yaml_dict, file,sort_keys=False)

    return yaml_file_name

if __name__ == '__main__':
    yaml_file_name = write_yaml('DTU_10MW_RWT.fst')
    turbine, controller = tune_ROSCO(yaml_file_name)

    # Plot rotor performance
    turbine.Cp.plot_performance()
    plt.show()
