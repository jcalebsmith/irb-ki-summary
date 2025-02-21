# Define messages with their tracking IDs
messages_dict = {
    "section1": [
        "Who can take part in this study?",
        "What are the eligibility criteria for this study?",
        "Are children eligible to participate in this study, either as primary participants or in any other capacity?",
        (
            "Choose the text below that is most appropriate.\n"
            "---\n\n"
            "If children are eligible to participate in the study, write the following text verbatim:\n"
            "You, or your child, may be eligible to take part in a research study. Parents or legal guardians who are giving permission for a child's participation in the research, note that in the sections that follow the word 'you' refers to 'your child'. This form contains information that will help you decide whether to join the study. All of the information in this form is important. Take time to carefully review this information. After you finish, you should talk to the researchers about the study and ask them any questions you have. You may also wish to talk to others such as your friends, family, or other doctors about your possible participation in this study. If you decide to take part in the study, you will be asked to sign this form. Before you do, be sure you understand what the study is about.\n\n"
            "Otherwise, if children are not eligible to participate in the study, or it is not possible to determine whether they are, then write the following text verbatim:\n"
            "You may be eligible to take part in a research study. This form contains important information that will help you decide whether to join the study. Take the time to carefully review this information. You should talk to the researchers about the study and ask them any questions you have. You may also wish to talk to others such as your family, friends, or other doctors about joining this study. If you decide to join the study, you will be asked to sign this form before you can start study-related activities. Before you do, be sure you understand what the research study is about."
        )
    ],
    "section4": [
        "What is the disease or condition targeted by the research study?",
        "What is the purpose or objective of the research study?",
        "How many people are expected to take part in the research study?",
        "Will the research study involve the collection of biological specimens such as blood, urine, tissue, cells, DNA, etc.?", 
        "What types of specimens will be collected and for what purposes?",
        (
            "You have been provided with template text and instructions below. To customize the text:\n"
            "1. Make a decision at each choice point indicated by angle brackets (<< >>) with options separated by slashes (//). Select the option that best matches the study particulars. If the existing options are not appropriate, you may choose to omit them or to create a more appropriate alternative.\n"
            "2. Replace placeholders enclosed in double brackets ([[ ]]) with pertinent details based on your understanding of the research study.\n"
            "3. Use lay-friendly language to describe the study. Do not use technical or scientific jargon unless there is no plain language alternative or converting to plain language would change the meaning of the text, such as in the case of disease or procedure names.\n"
            "5. When technical terms, scientific jargon, or acronyms must be used, attempt to define them using plain language the first time they are used. For example, 'This research is studying DIPG (diffuse intrinsic pontine glioma), a type of brain tumor that occurs in children.'\n"
            "---\n\n"
            "This research is << studying // collecting >> << a // a new //  >> [[state the general category of the object of the study, for example: 'drug', 'device', 'procedure', 'information', 'biospecimens', 'behavioral change', 'diagnostic tool', etc. If applicable, also indicate whether or not the object of the study has already been approved by the Food and Drug Administration (FDA) and for what]] in << people // large numbers of people // small numbers of people // children // large numbers of children // small numbers of children >>. The purpose is to [[briefly describe the purpose of the study]]. This study will [[briefly describe goals or objectives]]. Your health-related information will be collected during this research. [[If any biospecimen collection will be performed, indicate it here; otherwise, do not mention biospecimen collection]]."
        )
    ],
    "section5": [
        "Does the study involve randomization? Answer this question by checking the Informed Consent document for any of the following words: 'randomize', 'randomization', 'randomized'? If any of these EXACT terms are present, then the study involves randomization and you should respond, 'Yes, this study involves randomization.' Otherwise you should respond, 'No, the study does not involve randomization.'",
        "Review the Informed Consent document with the aim of identifying if it is a 'washout' study. A 'washout' study is characterized by requiring participants to discontinue certain prescribed medications for a period BEFORE or DURING the study. This discontinuation is typically to ensure that the effects of the study treatments can be observed without interference from other medications. Analyze the document for any instructions or requirements that align with this definition of a washout study. Based on your analysis, determine if the provided example text indicates that the study is a washout study. Respond with a clear 'Yes' or 'No'.",
        (
            "You have been provided with template text and instructions after the triple dashes below.\n"
            "Choose the text that is most appropriate based on what you have learned about this research study.\n"
            "When you encounter a choice enclosed in double angle brackets and delimited by double forward slashes (<<choice one // choice two>>), replace it with the choice that best fits the study's specifics. If you do not see an appropriate choice, then you may choose not to include any of the choices in your response or you may choose to generate an additional choice that is more appropriate. \n"
            "When you encounter a phrase in this text that is enclosed by double brackets ([[example instructions]]), replace it with relevant details derived from the STUDY INFORMATION provided above. \n\n"
            "---\n\n"
            "Step 1: If the study involves randomization, write the following text, otherwise skip this step:\n"
            "\n\nThis study involves a process called randomization. This means that the << drug // device // procedure >> you receive in the study is not chosen by you or the researcher. The study design divides study participants into separate groups, based on chance (like the flip of a coin), to compare different treatments or procedures. If you decide to be in the study, you need to be comfortable not knowing which study group you will be in.\n\n"
            "Step 2: If the study requires me to stop taking any medications before I can participate, write the following text, otherwise skip this step:\n"
            "\n\nThis study may require you to stop taking certain medications before and possibly during the research study. If you decide to be in the study, you should understand that some symptoms that were controlled by that medication may worsen.\n\n"
            "If both Step 1 and Step 2 are skipped, meaning the study neither involves randomization nor requires me to stop taking a particular medication before I can participate, then simply write an empty space: "
        )
    ],
    "section6": [
        (
            "Imagine that I am the study participant and you are explaining the most important risks that are introduced or enhanced because of participation in this research study to me.\n"
            "Rather than trying to explain every risk, focus on the risks that will cause me pain or emotional distrees. What are the most important risks that you would explain to me?\n"
            "Do not include risks associated with standard of care treatments. Only include risks that could reasonably be introduced or enhanced due to participation in this research study.\n"
            "Use plain language to describe the risks with few words. Your response should be no more than 3 sentences in length."
            ),
        (
            "You have been provided with template text after the triple dashes below. Adhere to this text in your response. When you encounter a phrase in this text that is enclosed by double brackets ([[example instructions]]), replace it with relevant details based on what you have learned about this research study. \n\n"
            "---\n\n"
            "There can be risks associated with joining any research study. The type of risk may impact whether you decide to join the study. For this study, some of these risks may include [[Briefly describe the risks while maintaining a formal tone]]. More detailed information will be provided later in this document."
        )
    ],
    "section7": [
        (
            "Imagine that I am the study participant and you are explaining the benefits of participating in this study. \n"
            "Create a list of the benefits and categorize them based on whether they will directly benefit me. \n"
            "Do not mention financial compensation.\n"
            "---\n\n"
            "[Direct personal benefits to me]\n"
            "<List direct personal benefits to me. If there are no direct personal benefits me, then skip this section>\n\n"
            "[Other potential benefits]\n"
            "<List other significant potential benefits>"
            ),
        (
            "You have been provided with template text after the triple dashes below. Adhere to this text in your response. "
            "When you encounter a choice enclosed in double angle brackets and delimited by double forward slashes (<<choice one // choice two>>), "
            "replace it with the choice that best fits the study's specifics. If you do not see an appropriate choice, then you may choose not to include "
            "any of the choices in your response or you may choose to generate an additional choice that is more appropriate."
            "\n\n"
            "When you encounter a phrase in this text that is enclosed by double brackets ([[example instructions]]), replace it with relevant details based "
            "on what you have learned about this research study.\n"
            "If there are no meaningful direct personal benefits to me, then select the second choice in the template text below. Otherwise, select the first choice.\n"
            "---\n\n"
            "<<This study may offer some benefit to you now or others in the future by "
            "[[Briefly summarize benefits based on what you have learned about this research study. Make sure the summarized text fits with the rest of this sentence and doesn't repeat or restate information that has already been provided.]]>> "
            "// "
            "This study may not offer any benefit to you now but may benefit others in the future by "
            "[[Briefly summarize potential benefits based on what you have learned about this research study. Make sure the summarized text fits with the rest of this sentence and doesn't repeat or restate information that has already been provided.]]>>. More information will be provided later in this document."
        )
    ],
    "section8": [
        "How much of my time, in total, will be needed to take part in this study? How long will I be in the study? What is the total duration of the study? In other words, how much of my time will be taken up by the study and how long will the overall study last?",
        (
            "After the triple dashes below, you have been provided with template text. Adhere to this text in your response, replacing any double bracketed instructions ([[example instructions]]), with relevant information about the research study.\n"
            "---\n\n"
            "The study will take [[Indicate how long the subject will be in the study based on what you have learned about this research study]]."
        )
    ],
    "section9": [
        "If I decide not to take part in this study, what other options do I have?",
        (
            "If participating in the study will not affect my current or future treatment/care options, or if this question is not applicable to this study, respond with the following text: \n"
            "'Even if you decide to join the study now, you are free to leave at any time if you change your mind.'\n\n"
            "Otherwise, respond with the following text:\n"
            "'You can decide not to be in this study. Alternatives to joining this study include [[Based on what you have learned about this research study, briefly specify potential treatment/care alternatives for this disease or condition such as the current standard of care]].\n\n"
            "Even if you decide to join the study now, you are free to leave at any time if you change your mind.'"
        )
    ]
}
