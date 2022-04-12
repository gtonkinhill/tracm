import os
import sys
import argparse
from datetime import date
import numpy as np

from MTRAN import pairsnp
from .transcluster import calculate_trans_prob
from .utils import check_positive_int, check_positive_float
from .__init__ import __version__


def main():

    parser = argparse.ArgumentParser(
        description="Estimates pairwise SNP and transmission distances between each pair of samples aligned to the same reference genome.",
        prog="dist",
    )

    io_opts = parser.add_argument_group("Input/output")

    io_opts.add_argument(
        "--msa",
        dest="msa_files",
        required=True,
        help="Input fasta files formatted by the align and merge functions",
        type=os.path.abspath,
        nargs="+",
    )

    io_opts.add_argument(
        "--meta",
        dest="metadata",
        required=True,
        help="""Location of metadata in csv format. The first column must include the 
        sequence names and the second column must include sampling dates.""",
        type=os.path.abspath,
    )

    io_opts.add_argument(
        "-o",
        "--output",
        dest="output_file",
        required=True,
        help="name of the output file to store the pairwise distance estimates.",
        type=str,
    )

    snpdist = parser.add_argument_group("SNP distance options")

    snpdist.add_argument(
        "-D",
        "--snp_threshold",
        dest="snp_threshold",
        help="Only output those transmission pairs with a SNP distance <= D",
        type=check_positive_int,
        default=2147483647,
    )

    transdist = parser.add_argument_group("Transmission distance options")

    transdist.add_argument(
        "--clock_rate",
        dest="clock_rate",
        help="clock rate as defined in the transcluster paper (SNPs/genome/year) default=1e-3 * 29903",
        type=check_positive_float,
        default=1e-3 * 29903,
    )

    transdist.add_argument(
        "--trans_rate",
        dest="trans_rate",
        help="transmission rate as defined in the transcluster paper (transmissions/year) default=73",
        type=check_positive_float,
        default=73,
    )

    transdist.add_argument(
        "-K",
        "--trans_threshold",
        dest="trans_threshold",
        help=(
            "Only outputs those pairs where the most likely number of intermediate hosts <= K"
        ),
        type=check_positive_int,
        default=None,
    )

    # Other options
    parser.add_argument(
        "-t",
        "--threads",
        dest="n_cpu",
        help="number of threads to use (default=1)",
        type=check_positive_int,
        default=1,
    )

    parser.add_argument(
        "--quiet",
        dest="quiet",
        help="turns off some console output",
        action="store_true",
        default=False,
    )

    parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__
    )

    args = parser.parse_args()

    # Load dates
    if not args.quiet:
        print("Loading metadata...")

    dates = {}
    with open(args.metadata, "r") as infile:
        next(infile)
        for line in infile:
            line = line.strip().split(",")
            dates[line[0]] = (line[1], date.fromisoformat(line[1]))

    if not args.quiet:
        print("Estimating transmission distances...")

    with open(args.output_file, "w") as outfile:
        outfile.write("sampleA,sampleB,date difference,SNP distance,transmission distance,expected K\n")
        for msa in args.msa_files:
            # Estimate SNP distances
            if not args.quiet:
                print("Calculating pairwise snp distances for %s" % msa)
            # I, J, dist, names
            snp_dists = pairsnp(
                fasta=[msa],
                n_threads=args.n_cpu,
                dist=args.snp_threshold
            )
            names = snp_dists[3]

            # Estimate transmission distances
            if not args.quiet:
                print("Inferring transmission probabilities for %s" % msa)
            transmission_dists, expectedk, datediff = calculate_trans_prob(
                snp_dists[:3],
                sample_dates=dates,
                K=100,
                lamb=args.clock_rate,
                beta=args.trans_rate,
                samplenames=snp_dists[3],
                log=False)

            # Write output
            if not args.quiet:
                print("Saving distances for %s" % msa)
            for i, j, dateD, snpD, expK, tranD  in zip(
                snp_dists[0], snp_dists[1], datediff, snp_dists[2], expectedk, transmission_dists
            ):
                outfile.write(
                    ",".join(
                        [names[i], names[j], str(dateD), str(int(snpD)), str(tranD), str(expK)]
                    )
                    + "\n"
                )

    return


if __name__ == "__main__":
    main()
