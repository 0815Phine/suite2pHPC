import suite2p
import sys

# define paths
# workspace directory
datapath = sys.argv[1:][0]

# load default settings
ops = suite2p.default_ops()

# recording related settings
ops['tau'] = 1.3
ops['fs'] = 15.2
ops['nchannels'] = 2
ops['functional_chan'] = 1
ops['nplanes'] = 1
ops['input_format'] = "nd2"

# registration settings
ops['do_bidiphase'] = True
ops['nimg_init'] = 800
ops['batch_size'] = 500
ops['smooth_sigma'] = 2
ops['smooth_sigma_time'] = 1
ops['two_step_registration'] = True

# nonrigid registration settings
ops['snr_thresh'] = 1.3
ops['maxregshiftNR'] = 8

# cell detection settings
ops['connected'] = True
ops['denoise'] = True
ops['may_iterations'] = 25
ops['max_overlap'] = 0.1
ops['threshold_scaling'] = 1.2
ops['nbinned'] = 3000
ops['high_pass'] = 50

# cellpose settings
ops['diameter'] = 12

# signal extraction
ops['allow_overlap'] = True

# spike detection
ops['spikedetect'] = False

# output settings
ops['save_mat'] = False
ops['delete_bin'] = True

# path related parameters
db = {
    'data_path': [datapath],
    'save_path0': [],
}

# run suite2p
output_ops = suite2p.run_s2p(ops=ops, db=db)