import yaml
from itertools import groupby
import numpy as np
import numpy.fft as fft
import metrics

hbar_evpj = 6.626e-34 * 6.242e18  # Convert Hz to eV
hc = 1239.84193 # Convert eV to nm

class fiber_run:
    def __init__(self, fname):
        self.fields  = []
        self.params  = {}
        self.metrics = {}

        # Read in fields from fname/E
        data_list = []
        with open(fname + "/E") as f:
            for k, g in groupby(f, lambda x: x=="\n"):
                if not k:
                    data_list.append(np.array([[float(x) for x in d.split(',')]
                                                for d in g if len(d.strip())]))

        # Turn raw field data in numpy arrays of complex numbers
        for data in data_list:
            re, im = data.T
            self.fields.append(re + 1j*im)

        # Load parameters
        with open(fname + "/params") as f:
            self.params = yaml.load(f)
            for key, val in self.params.items():
                self.params[key] = float(val)

        self.fix_units()
        self.metrics = metrics.populate_metrics(self, fname)

    # Returns a list of the spectra corresponding to each field
    def spectra(self, normed = False):
        return [spectrum(field, normed) for field in self.fields]

    def fix_units(self):
        # nanometers
        self.params['lambda'] = self.params['lambda']*1e9
        # microjoules
        self.params['Energy'] = self.params['Energy']*1e6
        # femtoseconds
        self.params['Tfwhm'] = self.params['Tfwhm']*1e15
        # femtoseconds
        self.params['tmax'] = self.params['tmax']*1e15
        # microns
        self.params['fiberD'] = self.params['fiberD']*1e6

    def make_time_scale(fiber_run, om=-15):
        p = fiber_run.params
        # Make freq axis
        Nt = p["Nt"]
        dt     = p["tmax"]/(Nt-1)        # Time step

        points = np.arange(-Nt/2, Nt/2, 1)
        return points * dt

    # Returns the frequency axis associated with the spectra stored in the run.
    # Order of mantiude (om) alters power of values. I.E. om=12 returns THz
    def make_freq_scale(fiber_run, om=12):
        p = fiber_run.params
        # Make freq axis
        Nt = p["Nt"]
        tmax = p["tmax"]
        points = np.arange(-Nt/2, Nt/2, 1)

        # lambda is in nm so speed of light needs to be in nm/s
        # tmax is in femto seconds, hence 1e15
        f = 1e15*points/tmax + 299792458e9/p["lambda"]
        return f / 10**om 

    # Returns the energy axis associated with the spectra stored in the run.
    # Order of mantiude (om) alters power of values. I.E. om=0 returns eV.
    def make_energy_scale(self, om=0):
        f = self.make_freq_scale(om=0)
        return f * hbar_evpj / 10**om

    # Returns the wavelength axis associated with the spectra stored in the run.
    # Order of magnitude (om) alters power of values. I.E. om=-9 returns nm.
    def make_wavelength_scale(self, om=-9):
        e = self.make_energy_scale()
        e = e[np.where(e >= 0)]

        return hc / e / 10**(om+9)

    # Applies the jacobian transformation of converting Hz into eV for the spectra
    # associated with a fiber run. Returns the modified spectra.
    # if normed = True, normalizes spectra before returning.
    def apply_jacob(self, normed = False):
        spectra = self.spectra()
        e = self.make_energy_scale()

        spectra = [spectrum[np.where(e >= 0)] for spectrum in spectra]
        e = e[np.where(e >= 0)]
        if normed:
            spectra = [spectrum * hc/np.power(e,2) for spectrum in spectra]
            return [spectrum/max(spectrum) for spectrum in spectra]
        else:
            return [spectrum * hc/np.power(e,2) for spectrum in spectra]

def flip_spectrum(spectrum, mid_ind):
        new = np.zeros(np.size(spectrum))
        for i,_ in enumerate(spectrum):
            new[i] = spectrum[2*mid_ind - i]
        return new

def spectrum(field, normed = False):
    # Flip field to have something moving in the right direction.
    transform = np.power(np.abs(fft.fftshift(fft.fft(fft.fftshift(np.flip(field,0))))),2)
    if normed:
        return transform/np.max(transform)
    else:
        return transform
