import argparse
import os
import sys

def main():
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--repos-config', default="./repos.config", help='Path to file with repos config')
    parser.add_argument('--workspace', default="./workspace", help="path to workspace where cloned repos will be placed")
    parser.add_argument('project', help="Source project from Juniper organization")
    args = parser.parse_args()
    print(args)


if __name__ == "__main__":
    main()
