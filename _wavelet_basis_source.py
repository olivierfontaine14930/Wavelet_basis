from typing import Any, Optional, Sequence, Tuple, Type, TypeVar
import pandas as pd
import numpy as np
import re
import os
import sys
import csv
import math
import scipy.io as sio
from scipy.interpolate import interp1d
from os.path import dirname, join
from skfda.representation.basis import Basis
from skfda._utils import _to_domain_range, _reshape_eval_points 


T = TypeVar("T", bound = 'Wavelets')

class wavelet(Basis):


    r"""
    .. math::
    Generally speaking, a wavelet basis in L_2(\mathbb{R}) is a collection of functions obtained as translations and dilations of a scaling function \phi and a mother
    wavelet \psi. The function \phi is constructed as a solution of the dilation
    equation: \\
    \phi(x) = \sqrt{2} \underset{l}{\sum h_l \phi(2x − l)} \\
    for a given set of filter coefficients hl that satisfy suitable conditions. \\
    
    The function \psi is defined from \phi as \\
        \psi(x) = sqrt{2} \underset{l}{\sum g_l \phi(2x − l)} \\

    with filter coefficients gl often defined as \\
        g_l = (−1)^l h_{1−l} \\

    The wavelet collection is obtained by translations and dilations as \\
        \phi_{j,k}(x) = 2^{j/2} \phi(2^j x − k) and \psi_{j,k}(x) = 2^{j/2} \psi(2^j x − k) \\

    Wavelet collections are particularly useful to approximate other functions. As it will be shown
    later, scaling functions give a good approximation of smooth functions while
    wavelets are particularly useful when dealing with functions that have local
    fluctuations. \\

    Mallat (1989) introduced orthonormal wavelet bases in the general context of the multiresolution analysis (MRA) as a decomposition of L2(IR)
    into a sequence of linear closed subspaces \{ V_j, j \in \mathbb{Z} \} such that \\
    (i) V_j \subset V_{j+1}, j \in \mathbb{Z} \\
    (ii) \underset{j}{ \bigcap V_j} = {0}, \underset{j}{\bigcup V_j} = L_2 (\mathbb{R}) \\
    (iii) f(x) \in V_j \Longleftrightarrow f(2x) \in V_{j−1}, f(x) \in V_j \Rightarrow f(x + k) \in V_j, k \in \mathbb{Z}. \\

    Here the dilation function \phi is such that the family \{phi(x − k), k \in \mathbb{Z} \}
    is an orthonormal basis for V_0. The family \{ \phi_{j,k} (x), k \in \mathbb{Z} \} is then an
    orthonormal basis for V_j . If W_j indicates the orthogonal complement of V_j
    in V_{j+1}, i.e. V_j \oplus W_j = V_{j+1}, then L_2(\mathbb{R}) can be decomposed as \\
    L_2(\mathbb{R}) = \underset{j \in \mathbb{Z}}{\oplus W_j} (1) \\
    or, equivalently, as \\
    L_2(mathbb{R}) = V_{j_0} \underset{j \geq j_0}{\oplus W_j} (2) \\
    The family of wavelets \{ \psi_{j,k}(x), j,k \in \mathbb{Z} \} forms an orthonormal basis in
    L_2(\mathbb{R})."""

    def __init__(self, wavelet_mother = "db4", start_level = 1 , stop_level = 3 , domaine = [0,7], domain_range = None):
        if start_level <= stop_level:
            self.start_level = start_level
            self.stop_level = stop_level
             
        else:
            raise ValueError("stop_level must be higher than start_level")
        self.domaine = domaine
        self._domain_range = domain_range
        self.wavelet_mother = wavelet_mother
        if stop_level != 0:
            n_basis = len((self.get_translates(domaine, wavelet_mother, start_level, stop_level, 1))[0])*(self.stop_level - self.start_level + 2)
        elif stop_level == 0:
            n_basis = len((self.get_translates(domaine, wavelet_mother, start_level, stop_level, 0))[0])*(- self.start_level + 3)   

        if domain_range is not None:
            domain_range = _to_domain_range(domain_range)

            if len(domain_range) != 1:
                raise ValueError("Domain range should be unidimensional.")

            domain_range = domain_range[0]
    
        super().__init__(domain_range=domain_range, n_basis=n_basis)
        


    def wave_support(self,wname):

    #Function to return support for a given wavelet.

        """
        Parameters
        ----------
        wname : str, wavelet basis name
        
        Returns
        -------
        support : 1*2 List of the wavelet support.
        """

        if wname in ['db2','db3','db4','db5','db6','db7','db7','db8','db9','db10']:
            N = int(re.findall(r'\d+', wname)[0])
            support = [0,2*N-1]
        elif wname == 'dmey':
            support = [0,101]
        elif wname in ['sym4','sym5','sym10']:
            N = int(re.findall(r'\d+', wname)[0])
            support = [0,2*N-1]
        elif wname in ['coif1','coif2','coif3','coif4','coif5']:
            N = int(re.findall(r'\d+', wname)[0])
            support = [0,6*N-1]
        else:
            support = np.nan

        return support #return a 1*2 list representing the wavelet support
    


    def translation_range(self,sample_support, w_name, level):
    #Function for calculating the span of translations for the current level.

        """
        Parameters
        ---------- 
        sample_support : 1*2 list, containing the sample support
        w_name : str, wavelet basis name
        level : int, Value for the integer scale level. Scale is calculated as 2**level

        Returns
        -------
        List : Start and stop translation values
        """



        w_support = self.wave_support(w_name)
        trans_range = np.zeros(2)
        trans_range[0] = math.floor((2**level)*sample_support[0] - w_support[1])
        trans_range[1] = math.ceil((2**level)*sample_support[1] - w_support[0])
    
        return trans_range #return an array with 2 values representing the translation values interval

    def get_translates(self,density_domain, wavelet, start_level, stop_level, wavelet_flag = 0):
    
    #Function for calculating the translations needed for a certain sample given a wavelet basis and starting resolution.
    #The function calculates the translates for scaling functions as default. If wavelet flag is set to 1, then translations are returned for wavelets functions.
    
        """"
        Parameters
        ----------
        density_domain : 1*2 list, containing the density domain 
        wavelet : str, wavelet basis name
        start_level : int, starting level for the father wavelet
        stop_level : int, last level of the mother wavelet scaling
        wavelet_flag : int, if the flag is set to 1, then density estimation is done with scaling + wavelets. The default is density estimation
        with the scaling function only. Default 0

        Returns
        -------
        List : List with translations of the scaling function
        array : array of wavelet translates
        """

    # get the translates
        trans_range = self.translation_range(density_domain, wavelet, start_level)
    # scal_translates
        scale_translates = []
        for i in range(int(trans_range[0]),int(trans_range[1]) + 1):
            scale_translates.append(i)
    # create an empty list
        wave_translates = []
    
    # if the wavelet flag is on 
        if wavelet_flag == 1:
            for i in range(start_level,stop_level+1):
                wave_translates_temp = []
                for i in range(int(trans_range[0]),int(trans_range[1]) + 1):
                    wave_translates_temp.append(i)
                wave_translates.append(wave_translates_temp)
    
        return scale_translates, np.array(wave_translates) #return (list containing the translation levels, array of wavelet translates)



    def create_basis(self, M, data_domain, type_transform, wavelet, start_level, stop_level):

    #Function for creating a Wavelet basis object defining a set of Wavelet functions with the specified period.

        """"
        Parameters
        ----------
        M : int, number of sampling points
        data_domain : List, 1*2 list, a domain of the input data
        type_transform : str, A string indicating type of basis chosen: 'wavelet'
        wavelet : str, wavelet basis name
        start_level : int, Starting level for the father wavelet (i.e scaling function) (j0). Must be an integer greater than 1.
        stop_level : int, Last level of the mother wavelet scaling (J). Must be >= start_level
        wavelet_flag : int, default {0}, if the flag is set to 1, then density estimation is done with scaling + wavelets. 
        The default is density estimation with the scaling function only.

        Returns
        -------
        array : The basis Matrix M * K where M is the number of sampling points (signal length) and K is the number of basis
        array : The array with sub arrays (M*Wi)having wavelet cofficients for the i-th level. where W = stop_level - start_level + 1
        """
    # get the current file path
        root = os.getcwd()
    # path for the type of wavelet 
        scale_type_path = root + '/' + wavelet + 'Tables.mat'
    # load the scaling function and wavelet
        scale_type = sio.loadmat(scale_type_path)
    # unpack values to get the scaling functions in separate lists
        supp_list = []
        for i in range(len(scale_type['supp'])):
            supp_list.append(scale_type['supp'][i][0])

        phi_list = []
        for i in range(len(scale_type['phi'])):
            phi_list.append(scale_type['phi'][i][0])

        psi_list = []
        for i in range(len(scale_type['psi'])):
            psi_list.append(scale_type['psi'][i][0])
    
    # condition to check type 
        if (type_transform == 'wavelet') & (stop_level == 0):
        
            stop_level = 1
            wavelet_flag = 0
        
            scale_translates, wave_translates = self.get_translates(data_domain, wavelet, start_level, stop_level, wavelet_flag)
        
            K = len(scale_translates)
            phiHere = np.zeros([M,K])
        
        # Generate time sample locations based on the input data
        # domain and number of signal samples
            t = np.linspace(data_domain[0], data_domain[1], M)
        
            for i in range(M):
                phi_arg = (2**start_level) * t[i] - scale_translates
                f = interp1d(supp_list,phi_list,fill_value= 0,bounds_error=False)
                phi_x = 2**(2/2) * f(phi_arg)
                for k in range(len(phi_x)):
                    phiHere[i][k] = phi_x[k]
        
        # return null value       
            psiHere = np.nan
    
        if (type_transform == 'wavelet') & (stop_level != 0):
            
            wavelet_flag = 1
                
            scale_translates, wave_translates = self.get_translates(data_domain, wavelet, start_level, stop_level, wavelet_flag)
        
            K = len(scale_translates)
            phiHere = np.zeros([M,K])
        
        # Generate time sample locations based on the input data
        # domain and number of signal samples
            t = np.linspace(data_domain[0], data_domain[1], M)
        
            for i in range(M):
                phi_arg = (2**start_level) * t[i] - scale_translates
                f = interp1d(supp_list,phi_list,fill_value= 0,bounds_error=False)
                phi_x = 2**(2/2) * f(phi_arg)
                for k in range(len(phi_x)):
                    phiHere[i][k] = phi_x[k]
                
            W = len(wave_translates)
            psiHere = []
        
            for j in range(start_level,stop_level+1):
                idx = j - start_level
                Wj = len(wave_translates[idx])
                psiTemp = np.zeros([M,Wj])
                for i in range(M):
                    psi_arg = (2**j) * t[i] - wave_translates[idx]
                    f = interp1d(supp_list,psi_list,fill_value= 0,bounds_error=False)
                    psi_x = 2**(j/2) * f(psi_arg)
                    for k in range(len(psi_x)):
                        psiTemp[i][k] = psi_x[k]
                psiHere.append(psiTemp)
    
        return phiHere, psiHere
    



    def _evaluate(self, eval_points):


        wtype = 'wavelet'
       

        points = eval_points

        M = len(points)
        t = np.linspace(self.domaine[0], self.domaine[1], M)

        phi,psi = self.create_basis(M, self.domaine, wtype, self.wavelet_mother, self.start_level, self.stop_level)
        Base_eval = []
        for j in range(np.shape(phi)[1]):
            Base_evalj = []
            for i in range(np.shape(phi)[0]):
                Base_evalj.append([phi[i][j]])
            Base_eval.append(Base_evalj)    
            for l in range(np.shape(psi)[0]):
                Base_evaljl = []
                for i in range(np.shape(phi)[0]):
                    Base_evaljl.append([psi[l][i,j]])
                Base_eval.append(Base_evaljl)
        return(np.array(Base_eval))    

    


