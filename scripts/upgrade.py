"""
Script to upgrade Helm Chart on a Kubernetes cluster running BinderHub
"""
import os
import sys
import logging
import argparse
from subprocess import check_output
from HubClass.run_command import run_cmd, run_pipe_cmd

# Setup logging config
logging.basicConfig(
    level=logging.DEBUG,
    filename="upgrade.log",
    filemode="a",
    format="[%(asctime)s %(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def parse_args():
    """Parse command line arguments and return them"""
    parser = argparse.ArgumentParser(
        description="Script to upgrade a helm chart for a BinderHub deployment on Azure"
    )

    parser.add_argument(
        "-n",
        "--hub-name",
        type=str,
        default="hub23",
        help="BinderHub name/Helm release name",
    )
    parser.add_argument(
        "-z",
        "--chart-name",
        type=str,
        default="hub23-chart",
        help="Local Helm Chart name",
    )
    parser.add_argument(
        "-c",
        "--cluster-name",
        type=str,
        default="hub23cluster",
        help="Name of Azure Kubernetes Service",
    )
    parser.add_argument(
        "-g",
        "--resource-group",
        type=str,
        default="Hub23",
        help="Azure Resource Group",
    )
    parser.add_argument(
        "-s",
        "--subscription",
        type=str,
        default="Turing-BinderHub",
        help="Azure subscription for resources",
    )
    parser.add_argument(
        "--identity",
        action="store_true",
        help="Login to Azure using a Managed System Identity",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Performs a dry-run upgrade of the Helm Chart",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Adds debugging output to helm upgrade command",
    )

    return parser.parse_args()


class Upgrade:
    """Upgrade BinderHub Helm Chart"""

    def __init__(self, argsDict):
        """Set arguments as variables"""
        self.hub_name = argsDict["hub_name"]
        self.chart_name = argsDict["chart_name"]
        self.cluster_name = argsDict["cluster_name"]
        self.resource_group = argsDict["resource_group"]
        self.subscription = argsDict["subscription"]
        self.identity = argsDict["identity"]
        self.dry_run = argsDict["dry_run"]
        self.debug = argsDict["debug"]

    def upgrade(self):
        """Upgrade the Kubernetes cluster"""
        if self.dry_run:
            logging.info("THIS IS A DRY-RUN. HELM CHART WILL NOT BE UPGRADED.")

        # Login to Azure and update Helm Chart
        self.login()
        self.update_local_chart()

        # Helm Upgrade Command
        helm_upgrade_cmd = [
            "helm",
            "upgrade",
            self.hub_name,
            self.chart_name,
            "-f",
            os.path.join("deploy", "prod.yaml"),
            "-f",
            os.path.join(".secret", "prod.yaml"),
            "--wait",
        ]

        if self.dry_run and self.debug:
            # Run as dry-run with debug output
            helm_upgrade_cmd.extend(["--dry-run", "--debug"])
            logging.info(
                "Performing a dry-run helm upgrade with debugging output"
            )
        elif self.dry_run and (not self.debug):
            # Run as dry-run
            helm_upgrade_cmd.append("--dry-run")
            logging.info("Performing a dry-run helm upgrade")
        elif (not self.dry_run) and self.debug:
            # Run with debug output
            helm_upgrade_cmd.append("--debug")
            logging.info("Performing a helm upgrade with debugging output")
        else:
            logging.info("Upgrading helm chart")

        result = run_cmd(helm_upgrade_cmd)
        if result["returncode"] == 0:
            logging.info(result["output"])
        else:
            logging.error(result["err_msg"])
            raise Exception(result["err_msg"])

        self.print_pods()

    def login(self):
        """Login to Azure"""
        login_cmd = ["az", "login"]

        if self.identity:
            login_cmd.append("--identity")
            logging.info("Logging into Azure with a Managed System Identity")
        else:
            logging.info("Logging into Azure")

        result = run_cmd(login_cmd)
        if result["returncode"] == 0:
            logging.info("Successfully logged into Azure")
        else:
            logging.error(result["err_msg"])
            raise Exception(result["err_msg"])

        # Set Azure subscription
        logging.info(f"Setting Azure subscription: {self.subscription}")
        sub_cmd = ["az", "account", "set", "-s"]

        # Catch subscription names that may have whitespace and wrap them in
        # double quotes
        if " " in self.subscription:
            sub_cmd.append(f'"{self.subscription}"')
        else:
            sub_cmd.append(self.subscription)

        result = run_cmd(sub_cmd)
        if result["returncode"] == 0:
            logging.info(
                f"Successfully set Azure subscription: {self.subscription}"
            )
        else:
            logging.error(result["err_msg"])
            raise Exception(result["err_msg"])

        # Set kubectl context
        logging.info(f"Setting kubectl context for: {self.cluster_name}")
        cmd = [
            "az",
            "aks",
            "get-credentials",
            "-n",
            self.cluster_name,
            "-g",
            self.resource_group,
        ]
        result = run_cmd(cmd)
        if result["returncode"] == 0:
            logging.info(result["output"])
        else:
            logging.error(result["err_msg"])
            raise Exception(result["err_msg"])

        # Initialise Helm
        logging.info("Initialising Helm")
        cmd = ["helm", "init", "--client-only"]
        result = run_cmd(cmd)
        if result["returncode"] == 0:
            logging.info(result["output"])
        else:
            logging.error(result["err_msg"])
            raise Exception(result["err_msg"])

    def update_local_chart(self):
        """Updating local chart"""
        logging.info(f"Updating local chart dependencies: {self.chart_name}")
        os.chdir(self.chart_name)

        update_cmd = ["helm", "dependency", "update"]
        result = run_cmd(update_cmd)
        if result["returncode"] == 0:
            logging.info(result["output"])
        else:
            logging.error(result["err_msg"])
            raise Exception(result["err_msg"])

        os.chdir(os.pardir)

    def print_pods(self):
        """Print the pods"""
        logging.info("Fetching the Kubernetes pods")
        cmd = ["kubectl", "get", "pods", "-n", self.hub_name]
        result = run_cmd(cmd)
        if result["returncode"] == 0:
            logging.info(result["output"])
        else:
            logging.error(result["err_msg"])
            raise Exception(result["err_msg"])


if __name__ == "__main__":
    args = parse_args()
    bot = Upgrade(vars(args))
    bot.upgrade()
