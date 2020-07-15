#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 14 16:59:25 2020

@author: egorkozlov
"""

import numpy as onp
import jax.numpy as jnp
np = jnp



def upper_envelope(bEV,a_implied,c_implied,agrid,li,um,R,sig):
    
    
    
    na, no = bEV.shape
    dt = c_implied.dtype
    c_out = np.zeros((na,0),dtype=dt)
    V_out = np.zeros((na,0),dtype=dt)
    
    def u(c):
        return c**(1-sig)/(1-sig)
    
    for io in range(no):
        
        ap = a_implied[:,io]
        Wp = bEV[:,io]
        cp = c_implied[:,io]
        
        ai_min = ap.min()
        ai_max = ap.max()
        
        
        # compute slopes, low and high poitnts
        
        ai_low = ap[:-1]
        ai_hig = ap[ 1:]
        ci_low = cp[:-1]
        ci_hig = cp[ 1:]
        Wi_low = Wp[:-1]
        Wi_hig = Wp[ 1:]
        
        
        
        ci_slope = (ci_hig - ci_low) / (ai_hig - ai_low)
        Wi_slope = (Wi_hig - Wi_low) / (ai_hig - ai_low)
        
        
        
        c_list = np.array([])
        V_list = np.array([])
        
        
        for ia in range(na):
            cthis = 0.0
            Vthis = -np.inf
            if agrid[ia] < ai_min:
                cthis = R*agrid[ia] + li[io]
                Vthis = um[io]*u(cthis) + bEV[0,io]
            elif agrid[ia] > ai_max:
                cthis = R*agrid[ia] + li[io] - agrid[-1]
                Vthis = um[io]*u(cthis) + bEV[-1,io]
            else:
                # true upper envelope
                # brute force with precomputed points and slopes
                athis = agrid[ia]
                for iap in range(na-1):
                    interp = (ai_low[iap] <= athis <= ai_hig[iap]) or (ai_low[iap] >= athis >= ai_hig[iap])
                    extrap_above = (iap == na-2) and (athis > ai_max) # this should not happen but anyways
                    
                    if interp or extrap_above:
                        c_guess = ci_low[iap] + ci_slope[iap] * (athis - ai_low[iap])
                        W_guess = Wi_low[iap] + Wi_slope[iap] * (athis - ai_low[iap])
                        
                        # value
                        V_guess = um[io]*u(c_guess) + W_guess

                        # select best value for this segment
                        if V_guess > Vthis:
                            Vthis = V_guess
                            cthis = c_guess
                            
            c_list = np.append(c_list,cthis)
            V_list = np.append(V_list,Vthis)
        
        
        c_out = np.hstack((c_out,c_list[:,None]))
        V_out = np.hstack((V_out,V_list[:,None]))
        
    return c_out, V_out



def upper_envelope_matrix(bEV,a_implied,c_implied,agrid,li,um,R,sig):
    
    sl = (slice(None,-1),slice(None))
    su = (slice(1,None),slice(None))
    ai_low = a_implied[sl]
    ai_high = a_implied[su]
    da = ai_high - ai_low
    ci_low = c_implied[sl]
    ci_high = c_implied[su]
    Wi_low = bEV[sl]
    Wi_high = bEV[su]
    ci_slope = (ci_high - ci_low)/da
    Wi_slope = (Wi_high - Wi_low)/da
    
    
    def u(c):
        return np.maximum(c,1e-8)**(1-sig)/(1-sig)
    
    
    # interpolate literally everyhing
    
    
    da = agrid[:,None,None] - ai_low[None,:,:]
    da_p = ai_high[None,:,:] - agrid[:,None,None]
    
    c_allint = ci_low[None,:,:] + ci_slope[None,:,:]*da
    W_allint = Wi_low[None,:,:] + Wi_slope[None,:,:]*da
    V_allint = um[None,None,:]*u(c_allint) + W_allint
    
    i_outside = (da*da_p < 0)
    
    
    V_check = V_allint - 1e20*i_outside
    i_best = V_check.argmax(axis=1)[:,None,:]
    
    
    
    c_egm = np.take_along_axis(c_allint,i_best,1).squeeze(axis=1)
    V_egm = np.take_along_axis(V_check,i_best,1).squeeze(axis=1)
    #assert False
    #assert np.all(V_egm>-1e15)
    #assert np.all(c_egm>0)
    # then correct those above and below grid
    
    
    c_below = R*agrid[:,None] + li[None,:]
    V_below = um[None,:]*u(c_below) + bEV[0:1,:]
    c_above = R*agrid[:,None] + li[None,:] - R*agrid[-1]
    V_above = um[None,:]*u(c_above) + bEV[-1:,:] # this can be a bad number
    
    aimin = a_implied.min(axis=0)
    aimax = a_implied.max(axis=0)
    
    i_below = (agrid[:,None] <= aimin[None,:])
    i_above = (agrid[:,None] >= aimax[None,:])
    i_egm = (~i_below) & (~i_above)
    
    c_out = i_egm*c_egm + i_below*c_below + i_above*c_above
    V_out = i_egm*V_egm + i_below*V_below + i_above*V_above
    
    #assert np.all(V_out>-1e19)
    #assert np.all(c_out>-1e19)
    
    return c_out, V_out
