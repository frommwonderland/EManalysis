import argparse
import sys

from analyzer.config import get_cfg_defaults
from analyzer.data import Dataloader
from analyzer.model import Clustermodel
from analyzer.vae import train
from analyzer.vae.dataset import MitoDataset


# RUN THE SCRIPT LIKE: $ python main.py --em datasets/human/human_em_export_8nm/ --gt datasets/human/human_gt_export_8nm/ --cfg configs/process.yaml

def create_arg_parser():
    '''
    Get arguments from command lines.
    '''
    parser = argparse.ArgumentParser(description="Model for clustering mitochondria.")
    parser.add_argument('--em', type=str, help='input directory em (path)')
    parser.add_argument('--gt', type=str, help='input directory gt (path)')
    parser.add_argument('--cfg', type=str, help='configuration file (path)')

    return parser


def main():
    '''
    Main function.
    '''
    # input arguments are parsed.
    arg_parser = create_arg_parser()
    args = arg_parser.parse_args(sys.argv[1:])
    print("Command line arguments:")
    print(args)

    # configurations
    if args.cfg is not None:
        cfg = get_cfg_defaults()
        cfg.merge_from_file(args.cfg)
        cfg.freeze()
        print("Configuration details:")
        print(cfg)
    else:
        cfg = get_cfg_defaults()
        cfg.freeze()
        print("Configuration details:")
        print(cfg)

    dataset = MitoDataset(cfg)

    if cfg.MODE.PROCESS == "iter":
        dataset.extract_scale_mitos()
        return
    elif cfg.MODE.PROCESS == "train":
        device = 'cpu'
        if cfg.SYSTEM.NUM_GPUS > 0:
            device = 'cuda'
        trainer = train.Trainer(dataset=dataset, batch_size=cfg.AUTOENCODER.BATCH_SIZE, train_percentage=0.7,
                                model_type=cfg.AUTOENCODER.ARCHITECTURE, epochs=cfg.AUTOENCODER.EPOCHS,
                                optimizer_type="adam", loss_function="l1", device=device)
        trainer.train()
        trainer.evaluate()
        return

    dl = Dataloader(cfg)
    em, gt = dl.load_chunk(vol='both')

    # dl.precluster(mchn='cluster')

    # fex = FeatureExtractor(em, gt, args.em, args.gt, dprc='iter')
    # tmp = fex.compute_seg_dist()
    # print(tmp)
    # fex.save_feat_dict(tmp, 'sizef.json')

    model = Clustermodel(cfg, em, gt, dl=dl, alg='kmeans', clstby='bysize')
    model.load_features()
    model.run()


if __name__ == "__main__":
    main()
