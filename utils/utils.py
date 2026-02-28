from scipy.io import loadmat
import pandas as pd
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt
import numpy as np
def import_experiment_data(experiment_name):
    data = loadmat(f"data/{experiment_name}/waveforms.mat")
    time = data["data"]["time"][0, 0].flatten()
    power_loss1 = data["data"]["loss1"][0, 0].flatten()
    power_loss2 = data["data"]["loss2"][0, 0].flatten()
    temp1 = data["data"]["T1"][0, 0].flatten()
    temp2 = data["data"]["T3"][0, 0].flatten()
    ta= data["data"]["Th"][0, 0].flatten()
    df=pd.DataFrame({
        "time": time,
        "power_loss1": power_loss1,
        "power_loss2": power_loss2,
        "T1": temp1,
        "T2": temp2,
        "Ta": ta
    })


    return df

class Experiment:
    def __init__(self, experiment_name,df=None,bundle=None):

        if bundle is not None:
            self.time = bundle[0,:]
            self.T1_meas = bundle[1,:]
            self.T2_meas = bundle[2,:]
            self.P1_meas = bundle[3,:]
            self.P2_meas = bundle[4,:]
            self.Ta_meas= bundle[5,:]
        else:    
            if df is None:
                self.df = import_experiment_data(experiment_name)
            else:
                self.df=df
            self.time = self.df["time"].values
            self.T1_meas = self.df["T1"].values
            self.T2_meas = self.df["T2"].values
            self.P1_meas = self.df["power_loss1"].values
            self.P2_meas = self.df["power_loss2"].values
            self.Ta_meas= self.df["Ta"].values


        self.Ts=self.time[1]-self.time[0]
        self.experiment_name = experiment_name
        self.load_interpolation()


    def load_interpolation(self):
        self.power_profile1 = interp1d(
        self.time,
        self.P1_meas,
        kind='linear',        # 'linear', 'cubic', 'previous'
        fill_value="extrapolate"
        )
        self.power_profile2 = interp1d(
        self.time,
        self.P2_meas,
        kind='linear',        # 'linear', 'cubic', 'previous'
        fill_value="extrapolate"
        )
        self.T1_profile = interp1d(
        self.time,
        self.T1_meas,
        kind='linear',        # 'linear', 'cubic', 'previous'
        fill_value="extrapolate"
    )
        self.T2_profile = interp1d(
        self.time,
        self.T2_meas,
        kind='linear',        # 'linear', 'cubic', 'previous'
        fill_value="extrapolate"
    )
        self.Ta_profile = interp1d(
        self.time,
        self.Ta_meas,
        kind='linear',        # 'linear', 'cubic', 'previous'
        fill_value="extrapolate"
    )



    def subsample_by_time(self,Ts_new,size):
        """
        Subsample to a desired sampling time Ts_new..
        """
        end_time=size*Ts_new
        t=self.time[self.time<=end_time]
        signals = [self.T1_meas, self.T2_meas]
        t = np.asarray(t)
        idx = [0]
        t_last = t[0]

        for k in range(1, len(t)):
            if t[k] - t_last >= Ts_new:
                idx.append(k)
                t_last = t[k]

        idx = np.array(idx)

        data={}
        data["time"]=t[idx]
        data["T1"]=signals[0][idx]
        data["T2"]=signals[1][idx]
        data["Ta"]=self.Ta[idx]
        return data
    
    def block_average(self,Ts_new,size=None):
        """
        Block-average signals over Ts_new windows.
        """
        if size is None:
            size = len(self.time)
        end_time=size*Ts_new
        t = np.asarray(self.time[self.time <= end_time])
        signals = [self.T1_meas, self.T2_meas,self.P1_meas,self.P2_meas,self.Ta]
        t0 = self.time[0]

        bins = np.floor((t - t0) / Ts_new).astype(int)
        unique_bins = np.unique(bins)

        t_out = []
        sig_out = [[] for _ in signals]

        for b in unique_bins:
            idx = np.where(bins == b)[0]
            t_out.append(np.mean(t[idx]))
            for i, s in enumerate(signals):
                sig_out[i].append(np.mean(s[idx]))

        data = {}
        data["time"] = np.array(t_out)
        data["T1"] = np.array(sig_out[0])
        data["T2"] = np.array(sig_out[1])
        data["power_loss1"] = np.array(sig_out[2])
        data["power_loss2"] = np.array(sig_out[3])
        data["Ta"] = np.array(sig_out[4])
        

        return data
    
    def get_resampled_data(self, dt,t_start=None, t_end=None, data=None):
        """
        Resamples the experiment data to a fixed time step (dt).
        Useful for ensuring the DMDc shift (k -> k+1) represents a consistent time.
        """
        if data is None:
            data = self.df
            
        t_raw = data["time"].values
        # If t_end is not provided, use the end of the dataset
        if t_end is None:
            t_end = t_raw[-1]

        if t_start is None:
            t_start=t_raw[0]
        
        # Create the new uniform timeline
        t_new = np.arange(t_start, t_end, dt)
        
        # Interpolate all columns to the new timeline
        # This is more robust than simple indexing for thermal transients
        reduced_data = {"time": t_new}
        for col in ["T1", "T2", "power_loss1", "power_loss2", "Ta"]:
            reduced_data[col] = np.interp(t_new, t_raw, data[col].values)
            
        return Experiment(df=pd.DataFrame(reduced_data), experiment_name=self.experiment_name)




    def plot_temperatures_and_power(self,data=None):
        fig, axs = plt.subplots(2, 1, sharex=True, figsize=(10, 7))

        if data is None:
            data=self.df
            
        t = data["time"].values
        T1 = data["T1"].values
        T2 = data["T2"].values
        P1 = data["power_loss1"].values
        P2 = data["power_loss2"].values
        
        # Power 1
        axs[0].plot(t, P1)
        axs[0].set_ylabel("Power [W]")
        axs[0].grid(True)
        

        # Temperature 1
        axs[1].plot(t, T1)
        axs[1].set_ylabel("T1 [°C]")
        axs[1].grid(True)
        

        # Power 2
        axs[0].plot(t, P2)
        axs[0].set_ylabel("Power [W]")
        axs[0].grid(True)
        axs[0].legend(["Power Loss 1", "Power Loss 2"])

        # Temperature 2
        axs[1].plot(t, T2)
        axs[1].set_ylabel("T2 [°C]")
        axs[1].set_xlabel("Time [s]")
        axs[1].grid(True)
        axs[1].legend(["Temperature 1", "Temperature 2"])

        plt.tight_layout()
        plt.savefig("graphics/"+self.experiment_name+"_data"+".svg", format="svg")
        plt.savefig("graphics/"+self.experiment_name+"_data"+".png", format="png", dpi=600)


        plt.show()
    
    def measure_temps(self,t):
        return self.T1_profile(t),self.T2_profile(t)
    
    def measure_power(self,t):
        return self.power_profile1(t),self.power_profile2(t)
    def measure_ambient_temp(self,t):
        return self.Ta_profile(t)

