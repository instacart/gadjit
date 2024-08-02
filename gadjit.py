import logging
import utils

from plugins.iga.conductorone import plugin_conductorone_cron
from plugins.llm.aigateway import aigateway


plugin_conductorone_cron.initialize()
aigateway.initialize()

def run(event):
    llm_plugin = aigateway
    iga_plugin = plugin_conductorone_cron

    access_requests = iga_plugin.get_access_requests(event)
    for access_request in access_requests:
        final_score = utils.compute_scores(access_request, llm_plugin)
        final_score = round(final_score, 2)

        comment = None
        if final_score >= 1:
            logging.info(f"Recommending {access_request.requester.email} be added to {access_request.entitlement.name} automatically.")
            comment = (f"The Instacart Security team's AI-powered access assistance bot "
                       f"has reviewed this access request and believes this access is appropriate. "
                       f"This is an automated message. [{final_score}]")
            iga_plugin.comment_request(access_request, comment)
            iga_plugin.approve_request(access_request)
        else:
            logging.info(f"Recommending {access_request.requester.email} NOT be added to {access_request.entitlement.name} automatically.")
            comment = (f"The Instacart Security team's AI-powered access assistance bot "
                       f"has reviewed this access request and found that most of the requestor's "
                       f"peers do not utilize this role as part of their job functions. "
                       f"Please carefully review this request and ensure it is appropriate "
                       f"to provide the requestor access. This is an automated message. [{final_score}]")
            iga_plugin.comment_request(access_request, comment)
