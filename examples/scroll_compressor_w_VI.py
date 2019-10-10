# This file is meant for experimentation with PDSim features and may not
# work for you.  Caveat emptor!!
#
from __future__ import division, print_function

# If being run from the folder that contains the PDSim source tree, 
# remove the current location from the python path and use the 
# site-packages version of PDSim
from math import pi

from PDSim.flow.flow_models import IsentropicNozzleWrapper
from PDSim.flow.flow import FlowPath
from PDSim.core.core import struct
from PDSim.scroll.core import Scroll
from PDSim.scroll import scroll_geo
from PDSim.core.containers import Tube
from PDSim.core.motor import Motor
from PDSim.scroll.core import Port
try:
    from PDSim.scroll.plots import plotScrollSet
    from PDSim.plot.plots import debug_plots # (Uncomment if you want to do the debug_plots)
    plotting = True
except ImportError as IE:
    print(IE)
    print('Plotting is disabled')
    plotting = False
    
from CoolProp import State
from CoolProp import CoolProp as CP

import scipy.interpolate as interp

import numpy as np

from matplotlib import pyplot as plt
import timeit

def Compressor(ScrollClass, Te=273, Tc=300, f=None, OneCycle=False, Ref='R410A', HDF5file='scroll_compressor.h5'):

    ScrollComp = ScrollClass()
    # This runs if the module code is run directly 
    
    ScrollComp.set_scroll_geo(83e-6, 3.3, 0.005, 0.006) #Set the scroll wrap geometry
    ScrollComp.set_disc_geo('2Arc', r2=0)
    ScrollComp.geo.delta_flank = 10e-6
    ScrollComp.geo.delta_radial = 10e-6
    
    ScrollComp.geo.delta_suction_offset = 0.0e-3
    ScrollComp.geo.phi_ie_offset = 0.0
    
    ScrollComp.omega = 3000/60*2*pi
    ScrollComp.Tamb = 298.0
    
    #Temporarily set the bearing dimensions
    ScrollComp.mech = struct()
    ScrollComp.mech.D_upper_bearing = 0.04
    ScrollComp.mech.L_upper_bearing = 0.04
    ScrollComp.mech.c_upper_bearing = 20e-6
    ScrollComp.mech.D_crank_bearing = 0.04
    ScrollComp.mech.L_crank_bearing = 0.04
    ScrollComp.mech.c_crank_bearing = 20e-6
    ScrollComp.mech.D_lower_bearing = 0.025
    ScrollComp.mech.L_lower_bearing = 0.025
    ScrollComp.mech.c_lower_bearing = 20e-6
    ScrollComp.mech.thrust_ID = 0.05
    ScrollComp.mech.thrust_friction_coefficient = 0.028 #From Chen thesis
    ScrollComp.mech.orbiting_scroll_mass = 2.5
    ScrollComp.mech.L_ratio_bearings = 3
    ScrollComp.mech.mu_oil = 0.008
    
    ScrollComp.h_shell = 0.02
    ScrollComp.A_shell = 0.05
    ScrollComp.HTC = 0.0
    
    ScrollComp.motor = Motor()
    ScrollComp.motor.set_eta(0.9)
    ScrollComp.motor.suction_fraction = 1.0
    
    Te = -20 + 273.15
    Tc = 20 + 273.15
    Tin = Te + 11.1
    DT_sc = 7
    temp = State.State(Ref,{'T':Te,'Q':1})
    pe = temp.p
    temp.update(dict(T=Tc, Q=1))
    pc = temp.p
    inletState = State.State(Ref,{'T':Tin,'P':pe})

    T2s = ScrollComp.guess_outlet_temp(inletState,pc)
    outletState = State.State(Ref,{'T':T2s,'P':pc})
    
    mdot_guess = inletState.rho*ScrollComp.Vdisp*ScrollComp.omega/(2*pi)
    
    ScrollComp.add_tube(Tube(key1='inlet.1',
                             key2='inlet.2',
                             L=0.3,
                             ID=0.02,
                             mdot=mdot_guess, 
                             State1=inletState.copy(),
                             fixed=1,
                             TubeFcn=ScrollComp.TubeCode))
    ScrollComp.add_tube(Tube(key1='outlet.1',
                             key2='outlet.2',
                             L=0.3,
                             ID=0.02,
                             mdot=mdot_guess, 
                             State2=outletState.copy(),
                             fixed=2,
                             TubeFcn=ScrollComp.TubeCode))
    
    ScrollComp.auto_add_CVs(inletState, outletState)
    
    ScrollComp.auto_add_leakage(flankFunc=ScrollComp.FlankLeakage, 
                                radialFunc=ScrollComp.RadialLeakage)
    
    FP = FlowPath(key1='inlet.2',
                  key2='sa', 
                  MdotFcn=IsentropicNozzleWrapper(),
                  )
    FP.A = pi*0.01**2/4
    ScrollComp.add_flow(FP)
    
    ScrollComp.add_flow(FlowPath(key1='sa', 
                                 key2='s1',
                                 MdotFcn=ScrollComp.SA_S1,
                                 MdotFcn_kwargs=dict(X_d=0.7)
                                 )
                        )
    ScrollComp.add_flow(FlowPath(key1='sa',
                                 key2='s2',
                                 MdotFcn=ScrollComp.SA_S2,
                                 MdotFcn_kwargs=dict(X_d=0.7)
                                 )
                        )
    
    ScrollComp.add_flow(FlowPath(key1='outlet.1',
                                 key2='dd',
                                 MdotFcn=ScrollComp.DISC_DD,
                                 MdotFcn_kwargs=dict(X_d=0.7)
                                 )
                        )
       
    ScrollComp.add_flow(FlowPath(key1='outlet.1',
                                 key2='ddd',
                                 MdotFcn=ScrollComp.DISC_DD,
                                 MdotFcn_kwargs=dict(X_d=0.7)
                                 )
                        )
#     ScrollComp.add_flow(FlowPath(key2 = 'outlet.1',
#                                  key2 = 'd1',
#                                  MdotFcn = ScrollComp.DISC_D1,
#                                  MdotFcn_kwargs = dict(X_d = 0.7)
#                                  )
#                         )
#     
#     FP = FlowPath(key1='outlet.1', 
#                   key2='dd', 
#                   MdotFcn=IsentropicNozzleWrapper(),
#                   )
#     FP.A = pi*0.006**2/4
#     ScrollComp.add_flow(FP)
#       
#     FP = FlowPath(key1='outlet.1', 
#                   key2='ddd', 
#                   MdotFcn=IsentropicNozzleWrapper(),
#                   )
#     FP.A = pi*0.006**2/4
#     ScrollComp.add_flow(FP)

    sim = ScrollComp
    phi_list = [sim.geo.phi_fie-2*pi-0.3]
    involute_list = ['i']
    D_list = [sim.geo.t]*len(phi_list)
    offset_list = [d/1.5 for d in D_list]
    X_d_list = [1.0]*len(phi_list)
    X_d_backflow_list = [0.0]*len(phi_list)
    port_tube_list = [0]

    Ltube_list = [0.001]
    IDtube_list = [0.003]
    # A superheated state
    Tsat_inj = (Te+Tc)/2 # [K]
    temp = State.State(Ref,{'T':Tsat_inj,'Q':1})
    temp = State.State(Ref,{'T':Tsat_inj+10,'P':temp.p})
    Ttube_list = [temp.T]
    RHOtube_list = [temp.rho]
    
    sim.fixed_scroll_ports = []
    for phi,involute,offset,D,parent,X_d,X_d_backflow in zip(phi_list,involute_list,offset_list,D_list,port_tube_list,X_d_list,X_d_backflow_list):
        p = Port()
        p.phi = phi
        p.involute = involute
        p.offset = offset
        p.D = D
        p.parent = parent
        p.X_d = X_d
        p.X_d_backflow = X_d_backflow
        sim.fixed_scroll_ports.append(p)
        
    more_keys = []
    for i, (L, ID, T, D) in enumerate(zip(Ltube_list, IDtube_list, Ttube_list, RHOtube_list)):
        sim.add_tube(Tube(key1='VITube'+str(i+1)+'.1',
                          key2='VITube'+str(i+1)+'.2',
                          L=L,
                          ID=ID,
                          mdot=mdot_guess*0.1, 
                          State1=State.State(inletState.Fluid,
                                             dict(T=T, D=D)
                                             ), 
                          fixed=1,
                          TubeFcn=sim.TubeCode
                          )
                    )
        more_keys.append('VITube'+str(i+1)+'.1')
    sim.additional_inlet_keys = more_keys
            
    # # This block can be uncommented to plot the scroll wrap with the VI ports
    # plotScrollSet(0, geo = sim.geo)
    # for port in sim.fixed_scroll_ports:
    #    x, y = scroll_geo.coords_inv(port.phi, sim.geo, 0, port.involute)
    #    nx, ny = scroll_geo.coords_norm(port.phi, sim.geo, 0, port.involute)
       
    #    x0 = x - nx*port.offset
    #    y0 = y - ny*port.offset
       
    #    t = np.linspace(0, 2*pi)
    #    plt.plot(port.D/2.0*np.cos(t) + x0, port.D/2.0*np.sin(t) + y0,'b')
       
    # plt.savefig('wrap_with_VI_ports.png',transparent=True)
    # plt.close()
    # quit()
            
    #  Calculate the areas between each VI port and every control volume
    sim.calculate_port_areas()
        
    for port in sim.fixed_scroll_ports:
        for partner in port.area_dict:
        
            #  Create a spline interpolator object for the area between port and the partner chamber
            A_interpolator = interp.splrep(port.theta, port.area_dict[partner], k=2, s=0)
            
            #  Add the flow between the EVI control volume and the chamber through the port
            sim.add_flow(FlowPath(key1='VITube'+str(port.parent+1)+'.2',
                                  key2=partner,
                                  MdotFcn=sim.INTERPOLATING_NOZZLE_FLOW,
                                  MdotFcn_kwargs=dict(X_d=port.X_d,
                                                      X_d_backflow=port.X_d_backflow,
                                                      upstream_key='VITube'+str(port.parent+1)+'.2',
                                                      A_interpolator=A_interpolator
                                                      )
                                 )
                         )
    
    ScrollComp.add_flow(FlowPath(key1='d1',
                                 key2='dd',
                                 MdotFcn=ScrollComp.D_to_DD))
    ScrollComp.add_flow(FlowPath(key1='d2',
                                 key2='dd',
                                 MdotFcn=ScrollComp.D_to_DD))
    
    #Connect the callbacks for the step, endcycle, heat transfer and lump energy balance
    ScrollComp.connect_callbacks(step_callback=ScrollComp.step_callback,
                                 endcycle_callback=ScrollComp.endcycle_callback,
                                 heat_transfer_callback=ScrollComp.heat_transfer_callback,
                                 lumps_energy_balance_callback=ScrollComp.lump_energy_balance_callback
                                 )
    
    t1 = timeit.default_timer()
    ScrollComp.RK45_eps = 1e-6
    ScrollComp.eps_cycle = 3e-3
    try:
        ScrollComp.precond_solve(key_inlet='inlet.1',
                                 key_outlet='outlet.2',
                                 solver_method='RK45',
                                 OneCycle=OneCycle,
                                 plot_every_cycle=False,
                                 #hmin = 1e-3
                                 eps_cycle=3e-3
                                 )
    except BaseException as E:
        print(E)
        raise

    print('time taken', timeit.default_timer()-t1)
    
    del ScrollComp.FlowStorage
    from PDSim.misc.hdf5 import HDF5Writer
    h5 = HDF5Writer()
    h5.write_to_file(ScrollComp, HDF5file)
    
    return ScrollComp
    
if __name__=='__main__':
    Compressor(Scroll)
