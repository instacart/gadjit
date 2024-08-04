import json
import logging

from json.decoder import JSONDecodeError
from gadjit.models import BaseGadjitScoringPlugin


class RequesterProfileAttributeProximityScoringPlugin(BaseGadjitScoringPlugin):
    """
    A plugin for computing scores based on user profile attributes proximity.

    Attributes:
        None

    Methods:
        compute_scores: Computes scores based on user profile attributes and entitlements.
        _match_user_properties_to_existing_group_members: Matches user properties to existing group members.
        _match_user_properties_to_entitlement_properties: Matches user properties to entitlement properties.
        __shared_words_percentage: Calculates the percentage of shared words between two strings.
    """

    def compute_scores(self, access_request, llm_plugin):
        """
        Compute the scores for an access request based on various criteria.

        Args:
            access_request (AccessRequest): An object representing the access request.
            llm_plugin (LLMPlugin): An object representing the plugin used for matching user properties.

        Returns:
            float: The final score calculated based on the access request criteria.
        """
        title_results = self._match_user_properties_to_existing_group_members(
            llm_plugin,
            "title_and_department",
            access_request.requester.title_and_department,
            access_request.entitlement.members,
        )
        supervisoryorg_results = self._match_user_properties_to_existing_group_members(
            llm_plugin,
            "SupervisoryOrganization",
            access_request.requester.supervisory_organization,
            access_request.entitlement.members,
        )

        # Compare the requestor's title and department to the description field on the entitlement
        entitlement_properties_results = (
            self._match_user_properties_to_entitlement_properties(
                llm_plugin,
                access_request.requester.title_and_department,
                access_request.entitlement.name,
                access_request.entitlement.description,
            )
        )

        # Prepare a dictionary for storing information about entitlement members who are proximate to our requestor
        existing_member_tally = {}

        # Process title match results
        for title_result in title_results:
            percentage = self.__shared_words_percentage(
                title_result.get("title_and_department"),
                access_request.requester.title_and_department,
            )
            existing_member_tally[title_result.get("user")] = (
                existing_member_tally.setdefault(title_result.get("user"), 0)
                + percentage
            )

        # Process supervisory organization match results
        for supervisoryorg_result in supervisoryorg_results:
            percentage = self.__shared_words_percentage(
                supervisoryorg_result.get("SupervisoryOrganization"),
                access_request.requester.supervisory_organization,
            )
            existing_member_tally[supervisoryorg_result.get("user")] = (
                existing_member_tally.setdefault(supervisoryorg_result.get("user"), 0)
                + percentage
            )

        # Get the highest three scores
        top_three_scores = sorted(existing_member_tally.values(), reverse=True)[:3]

        # Calculate the average of these scores if there are any scores
        final_score = 0
        if top_three_scores:
            final_score = sum(top_three_scores) / len(top_three_scores)
        logging.debug(f"Average of the highest three scores: {final_score}")

        logging.debug(
            f"Now inspecting entitlement_properties_results: {entitlement_properties_results}"
        )
        if entitlement_properties_results:
            # We scale the relevant group members score by the job title + description score
            final_score = final_score * entitlement_properties_results

        logging.debug(f"Final score: {final_score}")
        return final_score

    def _match_user_properties_to_existing_group_members(
        self, llm_plugin, field_type, field_value, entitlement_users
    ):
        """
        Match user properties to existing group members based on a specified field type.

        Args:
            llm_plugin: The plugin used for the query.
            field_type (str): The type of field being matched (e.g. 'title_and_department', 'SupervisoryOrganization').
            field_value: The value of the field being matched.
            entitlement_users: The list of users to match against.

        Returns:
            list: A list of users that match the specified criteria.

        Raises:
            ValueError: If the field type is not supported.
            JSONDecodeError: If there is an issue decoding the JSON response.
        """
        if field_type == "title_and_department":
            field_type_verbose = "job title"
            system_example_field_input = "Senior Analyst, Eng - Online Grocery"
            system_example_strongly_related = (
                "Staff Software Engineer, Eng - Online Grocery"
            )
            system_example_unrelated = "Staff Compliance Auditor, Eng - Security"
        elif field_type == "SupervisoryOrganization":
            field_type_verbose = "organizational unit"
            system_example_field_input = (
                "Eng Algorithms - Economics - Marketplace Optimization"
            )
            system_example_strongly_related = "Eng Algorithms - Search ML"
            system_example_unrelated = "Eng Marketplace - Growth Modeling"
        else:
            raise ValueError(f"Unsupported type '{field_type}'.")

        llm_result = self._generic_profile_field_query(
            llm_plugin,
            field_type,
            field_type_verbose,
            field_value,
            system_example_field_input,
            system_example_strongly_related,
            system_example_unrelated,
            entitlement_users,
        )

        if not llm_result:
            logging.warning("LLM provider did not complete its answer.")
            return None

        logging.debug(llm_result)

        try:
            results = json.loads(llm_result).get("overlap_users")
        except JSONDecodeError as e:
            logging.exception(
                f"The following content caused the JSONDecodeError: {llm_result}"
            )
            raise e

        if not results:
            return []

        return results

    def _generic_profile_field_query(
        self,
        llm_plugin,
        field_type,
        field_type_verbose,
        field_value,
        system_example_field_input,
        system_example_strongly_related,
        system_example_unrelated,
        entitlement_users,
    ):
        """
        Perform a query to find closely related group members to an applicant based on a specific field type.

        Args:
            llm_plugin: An instance of the llm_plugin class.
            field_type (str): The type of field to compare for similarity.
            field_type_verbose (str): A more descriptive version of the field type.
            field_value (str): The value of the field for the new applicant.
            system_example_field_input (str): An example value for the field type for the system prompt.
            system_example_strongly_related (str): An example strongly related field value for the system prompt.
            system_example_unrelated (str): An example unrelated field value for the system prompt.
            entitlement_users (dict): A dictionary of entitlement users with emails as keys and profile information as values.

        Returns:
            str: The query result from the llm_plugin.

        Notes:
            - The function generates a user prompt and a system prompt based on the input parameters.
            - The output from the query must follow a specific JSON format as described in the function.
            - The function limits the number of users in the output to a maximum of 5 best matches.
            - Matching criteria are based on conceptual similarity of field values.
            - Provides guidance for comparing job titles based on engineering career leveling progression.

        Raises:
            None
        """
        entitlement_users_flattened = []
        for email, profile in entitlement_users.items():
            # entitlement_users_flattened.append(f"{email}: {profile[field_type]}")
            # Send IDs to the LLM but not personal information like their email
            entitlement_users_flattened.append(
                f"{profile['id']}: {profile[field_type]}"
            )
        entitlement_users_flattened_string = "\n".join(
            reversed(entitlement_users_flattened)
        )

        user_prompt = (
            f"A new applicant wants to join the group. The applicant has the {field_type_verbose} "
            f'of:\n"{field_value}"\n\nThe group\'s '
            f"membership and {field_type_verbose}s are as follows:\n\n"
            f"{entitlement_users_flattened_string}"
        )

        system_prompt = (
            f"You will be provided a list of employee IDs currently within a user directory group, and their {field_type_verbose}. "
            f"You will also be provided information about a new applicant to the group, and their {field_type_verbose}. "
            f"Report back group members that closely match the applicant's {field_type_verbose}. Respond in JSON only without any markdown or formatting. "
            f"For example, for the input:\n\n"
            f"[start of example]\n"
            f"A new applicant wants to join the group. The applicant has a {field_type_verbose} of:\n"
            f'"{system_example_field_input}"\n\n'
            f"The group's membership list (employee ID and title) are as follows:\n\n"
            f"2UzZUNHoFtzbGuuNi0H6FZ0c2rY: {system_example_strongly_related}\n"
            f"2aQd22omPtj05gKmRNxRDvBekk2: {system_example_unrelated}\n"
            f"[end of example]\n\n"
            f"Should yield the following JSON structure:\n"
            f"{{\n"
            f'    "overlap_users": [\n'
            f"        {{\n"
            f'            "user": "2UzZUNHoFtzbGuuNi0H6FZ0c2rY",\n'
            f'            "{field_type}": "{system_example_strongly_related}"\n'
            f"        }}\n"
            f"    ]\n"
            f"}}\n\n"
            f"The output must follow this syntax specified above, with the key names as specified "
            f"('overlap_users', 'user', and '{field_type}'). There should only be one "
            f"'overlap_users' key in the JSON object. The output must be fully valid JSON.\n\n"
            f"If there is no user who matches the criteria, output:\n"
            f"{{\n"
            f'    "overlap_users": null\n'
            f"}}\n\n"
            f"Limit the number of users to describe in overlap_users to the 5 best matches at "
            f"maximum. A best match is one where the group member's {field_type_verbose} is "
            f"as conceptually similar to the group applicant's {field_type_verbose} as possible. "
            f"The similarities don't need to be perfect, but take your best guess.\n\n"
            f"If you are asked to find close matches to user job titles, be aware that our engineering career leveling progression is as follows:\n"
            f"Engineer is the level below Senior Engineer\n"
            f"Senior Engineer is the level below Senior Engineer II\n"
            f"Senior Engineer II is the level below Staff Engineer\n"
            f"Staff Engineer is the level below Senior Staff Engineer\n"
            f"Senior Staff Engineer is the level below Principal Engineer\n"
            f"Principal Engineer is the highest level of Engineer\n\n"
            f"When asked to compare job titles for similarities, approximately match the group applicant's title for job leveling. "
            f"It doesn't need to be a perfect match, just conceptually similar. For instance:\n"
            f"'Staff Machine Learning Engineer, Eng - IoT Devices' is similar to 'Staff Machine Learning Engineer, Sales Effectiveness'.\n"
            f"'Senior Staff Robotics Engineer, Eng - Robotics' is more similar to 'Staff Robotics Engineer, Eng - Robotics' than 'Senior Robotics Engineer, Eng - Robotics', because the career leveling progression is closer.\n"
            f"'Senior Staff Robotics Engineer, Eng - Robotics' is more similar to 'Senior Staff Compliance Engineer, Eng - Robotics' than 'Senior Robotics Engineer, Eng - Robotics', because the career leveling is closer across similar functional areas.\n"
        )

        return llm_plugin.query(system_prompt, user_prompt)

    def _match_user_properties_to_entitlement_properties(
        self,
        llm_plugin,
        task_target_profile_title_dept,
        entitlement_name,
        entitlement_description,
    ):
        """
        Match user properties to entitlement properties.

        Args:
            llm_plugin (plugin): The plugin used to query the LLM system for matching.
            task_target_profile_title_dept (str): The job title of the new applicant.
            entitlement_name (str): The name of the group controlling access.
            entitlement_description (str): The description of the group controlling access.

        Returns:
            float: The relationship score between the new applicant's job title and the group's access control.

        Raises:
            None

        Note:
        The function uses the LLM plugin to query and determine the relationship score between the job title and group access control based on provided information.
        The output must be in JSON format with the key 'relationship_score'.
        """
        user_prompt = (
            f"A new applicant wants to join the group. The applicant has the job title "
            f'of:\n"{task_target_profile_title_dept}"\n\nThe group\'s '
            f"name and description are as follows:\n\n"
            f"Group name: {entitlement_name}\n"
            f"Group description: {entitlement_description}"
        )

        system_prompt = (
            f"You will be provided the name and description of a group which controls access to a resource within our company. "
            f"For example, the group named \"AWS-Sales\" controls access to the Amazon Web Services (AWS) role called 'sales'. "
            f"You will also be provided the job title of a new applicant to the group. "
            f"You are to decide if the applicant's job title is a good match to the group that have requested access to, "
            f"on a scale of 0.5 to 1.5, where '0.5' means no relationship between the applicant's job title and what the role is "
            f"capable of performing, '1' means you cannot determine a score based on the information provided or that there's a possible "
            f"relationship between the applicant's job title and what the role is capable of performing, '1.2' means there is "
            f"likely a very strong relationship between the applicant's job title and what the role is capable of performing, and "
            f"'1.5' means there is complete confidence in the relationship between the applicant's job title and what the role is "
            f"capable of performing.\n"
            f"Respond in JSON only without any markdown or formatting. "
            f"For example, for the input:\n\n"
            f"[start of example]\n"
            f"A new applicant wants to join the group. The applicant has a job title of:\n"
            f'"Senior Sales Executive"\n\n'
            f"The group's name and description are as follows:\n\n"
            f"Group name: AWS-Accounting\n"
            f"Group description: AWS User role designated for the Accounting team. Limited S3 operations including listBuckets.\n"
            f"[end of example]\n\n"
            f"Should yield the following JSON structure:\n"
            f"{{\n"
            f'    "relationship_score": 0.5\n'
            f"}}\n\n"
            f"The output must follow this syntax specified above, with the key names as specified "
            f"('relationship_score')\n\n"
            f"Here is another example where the match is very strong:\n\n"
            f"[start of example]\n"
            f"A new applicant wants to join the group. The applicant has a job title of:\n"
            f'"Staff Security Engineer"\n\n'
            f"The group's name and description are as follows:\n\n"
            f"Group name: AWS-Security\n"
            f"Group description: AWS role designated for Security Team. This role includes PowerUser "
            f"(near full admin) on Security-Development account. On other accounts, permissions include "
            f"ability to read logs from S3, read object metadata (not content) on S3, Detective, and "
            f"Snapshots. Can view SSM maintenance logging, Billing, Access Analyzer, and inherits "
            f"AWS-Developer capabilities as well.\n"
            f"[end of example]\n\n"
            f"Should yield the following output:\n"
            f"{{\n"
            f'    "relationship_score": 1.5\n'
            f"}}\n\n"
            f"Again, if you cannot determine a score based on the information provided, output:\n"
            f"{{\n"
            f'    "relationship_score": 1\n'
            f"}}\n\n"
        )

        llm_result = llm_plugin.query(system_prompt, user_prompt)

        if not llm_result:
            logging.warning("LLM provider did not complete its answer.")
            return None

        try:
            results = json.loads(llm_result).get("relationship_score")
        except JSONDecodeError as e:
            logging.exception(
                f"The following content caused the JSONDecodeError: {llm_result}"
            )
            raise e

        if not results:
            return None

        return results

    def __shared_words_percentage(self, str1, str2):
        """
        Calculate the percentage of shared words between two strings.

        Args:
            str1 (str): The first string.
            str2 (str): The second string.

        Returns:
            float: The percentage of shared words.
        """
        # Tokenize and normalize the words (split by spaces and convert to lowercase)
        # A word is anything >= 2 chars
        set1 = set(word for word in str1.lower().split() if len(word) >= 2)
        set2 = set(word for word in str2.lower().split() if len(word) >= 2)

        # Calculate the intersection of both sets
        common_words = set1.intersection(set2)

        # Calculate the union of both sets
        all_words = set1.union(set2)

        # Calculate the percentage of shared words
        if len(all_words) == 0:
            return 0  # To avoid division by zero if both strings are empty
        return len(common_words) / len(all_words)
