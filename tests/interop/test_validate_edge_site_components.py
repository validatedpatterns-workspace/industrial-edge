import logging
import os

import pytest
from ocp_resources.route import Route
from validatedpatterns_tests.interop import application, components

from . import __loggername__

logger = logging.getLogger(__loggername__)

oc = os.environ["HOME"] + "/oc_client/oc"


@pytest.mark.test_validate_edge_site_components
def test_validate_edge_site_components():
    logger.info("Checking Openshift version on edge site")
    version_out = components.dump_openshift_version()
    logger.info(f"Openshift version:\n{version_out}")


@pytest.mark.validate_edge_site_reachable
def test_validate_edge_site_reachable(kube_config, openshift_dyn_client):
    logger.info("Check if edge site API end point is reachable")
    err_msg = components.validate_site_reachable(kube_config, openshift_dyn_client)
    if err_msg:
        logger.error(f"FAIL: {err_msg}")
        assert False, err_msg
    else:
        logger.info("PASS: Edge site is reachable")


@pytest.mark.validate_argocd_reachable_edge_site
def test_validate_argocd_reachable_edge_site(openshift_dyn_client):
    logger.info("Check if argocd route/url on edge site is reachable")
    err_msg = components.validate_argocd_reachable(openshift_dyn_client)
    if err_msg:
        logger.error(f"FAIL: {err_msg}")
        assert False, err_msg
    else:
        logger.info("PASS: Argocd is reachable")


@pytest.mark.check_pod_status_edge
def test_check_pod_status(openshift_dyn_client):
    logger.info("Checking pod status")
    projects = [
        "openshift-operators",
        "open-cluster-management-agent",
        "open-cluster-management-agent-addon",
        "manuela-stormshift-line-dashboard",
        "manuela-stormshift-machine-sensor",
        "openshift-gitops",
    ]
    err_msg = components.check_pod_status(openshift_dyn_client, projects)
    if err_msg:
        logger.error(f"FAIL: {err_msg}")
        assert False, err_msg
    else:
        logger.info("PASS: Pod status check succeeded.")


@pytest.mark.validate_manuela_stormshift_line_dashboard_reachable_edge_site
def test_validate_manuela_stormshift_line_dashboard_reachable_edge_site(
    openshift_dyn_client,
):
    namespace = "manuela-stormshift-line-dashboard"
    logger.info(
        "Check if manuela-stormshift-line-dashboard route/url on edge site is"
        " reachable"
    )

    try:
        for route in Route.get(
            dyn_client=openshift_dyn_client,
            namespace=namespace,
            name="line-dashboard",
        ):
            logger.info(route.instance)
            if "host" in route.instance.spec:
                line_dashboard_route_url = route.instance.spec.host
            else:
                line_dashboard_route_url = route.instance.status.ingress[0].host

    except NotFoundError:
        err_msg = f"Line dashboard url/route is missing in {namespace} namespace"
        logger.error(f"FAIL: {err_msg}")
        assert False, err_msg

    final_line_dashboard_route_url = f"{'http://'}{line_dashboard_route_url}"
    logger.info(f"line dashboard route/url : {final_line_dashboard_route_url}")

    bearer_token = edge_util.get_long_live_bearer_token(
        dyn_client=openshift_dyn_client,
        namespace="openshift-gitops",
        sub_string="argocd-dex-server-token",
    )
    if not bearer_token:
        err_msg = "Bearer token is missing for argocd-dex-server"
        logger.error(f"FAIL: {err_msg}")
        assert False, err_msg
    else:
        logger.debug(f"Bearer token : {bearer_token}")

    line_dashboard_route_response = edge_util.get_site_response(
        site_url=final_line_dashboard_route_url, bearer_token=bearer_token
    )

    logger.info(f"line dashboard route response : {line_dashboard_route_response}")

    if line_dashboard_route_response.status_code != 200:
        err_msg = "Line dashboard is not reachable. Please check the deployment."
        logger.error(f"FAIL: {err_msg}")
        assert False, err_msg
    else:
        logger.info("PASS: Line dashboard is reachable")


@pytest.mark.validate_argocd_applications_health_edge_site
def test_validate_argocd_applications_health_edge_site(openshift_dyn_client):
    logger.info("Get all applications deployed by argocd on edge site")
    projects = ["openshift-gitops", "industrial-edge-factory"]
    unhealthy_apps = application.get_argocd_application_status(
        openshift_dyn_client, projects
    )
    if unhealthy_apps:
        err_msg = "Some or all applications deployed on edge site are unhealthy"
        logger.error(f"FAIL: {err_msg}:\n{unhealthy_apps}")
        assert False, err_msg
    else:
        logger.info("PASS: All applications deployed on edge site are healthy.")
