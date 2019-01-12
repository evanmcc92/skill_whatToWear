# -*- coding: utf-8 -*-

import random
import logging
import urllib.request
import json
import math
import os

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import (
    AbstractRequestHandler, AbstractExceptionHandler,
    AbstractRequestInterceptor, AbstractResponseInterceptor)
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_core.handler_input import HandlerInput

from ask_sdk_model.ui import StandardCard
from ask_sdk_model.ui.ask_for_permissions_consent_card import AskForPermissionsConsentCard
from ask_sdk_model.ui.image import Image
from ask_sdk_model import Response


SKILL_NAME = "What to Wear"
HELP_MESSAGE = "You can ask what to wear, or, you can say exit... What can I help you with?"
HELP_REPROMPT = "What can I help you with?"
STOP_MESSAGE = "Goodbye!"
FALLBACK_MESSAGE = "The What to Wear skill can't help you with that. It can help give you an idea of what to wear today based off of the weather. What can I help you with?"
FALLBACK_REPROMPT = 'What can I help you with?'
EXCEPTION_MESSAGE = "Sorry. I cannot help you with that."
NOTIFY_MISSING_PERMISSIONS = ("Please enable Location permissions in "
                              "the Amazon Alexa app.")
permissions = ["read::alexa:device:all:address:country_and_postal_code"]

sb = SkillBuilder()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# Built-in Intent Handlers
class GetWhatToWearHandler(AbstractRequestHandler):
    """Handler for Skill Launch and GetNewFact Intent."""

    def __getDeviceLocation(self, system):
        deviceId = system.device.device_id
        apiEndpoint = system.api_endpoint
        apiAccessToken = system.api_access_token
        headers = {
            "Accept": "application/json",
            "Authorization": "Bearer %s" % (apiAccessToken)
        }
        url = "%s/v1/devices/%s/settings/address/countryAndPostalCode" % (apiEndpoint, deviceId)
        req = urllib.request.Request(url, headers=headers)
        try:
            response = urllib.request.urlopen(req)
        except urllib.error.HTTPError as e:
            logger.debug(e)
            return False

        deviceLocation = json.loads(response.read())
        deviceLocationZipCode = deviceLocation['postalCode']
        return deviceLocationZipCode

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (is_request_type("LaunchRequest")(handler_input) or
                is_intent_name("GetWhatToWearIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Responseå
        logger.info("In GetWhatToWearHandler")
        
        deviceLocation = ''
        if handler_input.request_envelope.request.intent:
            intent = handler_input.request_envelope.request.intent
            zipcode = intent.slots.get('zipcode').value
            city = intent.slots.get('city').value

            if zipcode:
                deviceLocation = zipcode
            if city:
                deviceLocation = city
            if not deviceLocation:
                deviceLocationAPICall = self.__getDeviceLocation(handler_input.request_envelope.context.system)
                if not deviceLocationAPICall:
                    handler_input.response_builder.speak(NOTIFY_MISSING_PERMISSIONS).set_card(AskForPermissionsConsentCard(permissions=permissions))
                    return handler_input.response_builder.response
                else:
                    deviceLocation = deviceLocationAPICall
        else:
            deviceLocationAPICall = self.__getDeviceLocation(handler_input.request_envelope.context.system)
            if not deviceLocationAPICall:
                handler_input.response_builder.speak(NOTIFY_MISSING_PERMISSIONS).set_card(AskForPermissionsConsentCard(permissions=permissions))
                return handler_input.response_builder.response
            else:
                deviceLocation = deviceLocationAPICall

        # build url
        apiKey = os.environ['apiKey']
        url = 'http://api.openweathermap.org/data/2.5/weather?q=%s,us&units=imperial&appid=%s' % (deviceLocation, apiKey)

        # get and load weather data
        weatherDataRaw = urllib.request.urlopen(url).read()
        weatherData = json.loads(weatherDataRaw)

        # get desired variables
        cityName = weatherData['name']
        weatherDescription = weatherData['weather'][0]['description']
        temp = math.ceil(weatherData['main']['temp'])
        humidity = math.ceil(weatherData['main']['humidity'])
        tempMin = math.ceil(weatherData['main']['temp_min'])
        tempMax = math.ceil(weatherData['main']['temp_max'])

        # determine what to wear
        imageURL = ''
        whatToWear = ''
        if temp <= 45:
            whatToWear = "a winter coat and long pants"
            imageURL = "https://upload.wikimedia.org/wikipedia/commons/4/42/FMIB_41384_Winter_traveling_dress%2C_common_throughout_the_Yukon_Valley.jpeg"
        elif 45 < temp <= 55:
            whatToWear = "a light coat and long pants"
            imageURL = "https://img.buzzfeed.com/buzzfeed-static/static/2013-10/enhanced/webdr03/19/3/enhanced-buzz-6188-1382168152-22.jpg?downsize=800:*&output-format=auto&output-quality=auto"
        elif 55 < temp <= 70:
            whatToWear = "a sweater or sweat shirt and long pants"
            imageURL = "https://storage.googleapis.com/relevant-magazine/2018/08/What-Mr.-Rogers-Can-Still-Teach-Us-1-720x720.jpg"
        elif 70 < temp <= 75:
            whatToWear = "a sleeved shirt and long pants"
            imageURL = "https://www.hotflick.net/flicks/2001_Ocean_s_Eleven/001OEL_George_Clooney_033.jpg"
        elif 75 < temp <= 80:
            whatToWear = "a short sleeved shirt and long pants"
            imageURL = "https://d1q0twczwkl2ie.cloudfront.net/wp-content/uploads/2018/02/ryan-gosling-rachel-mcadams-the-notebook.jpg"
        elif 80 < temp:
            whatToWear = "a short sleeved shirt or tank top with shorts"
            imageURL = "https://m.media-amazon.com/images/M/MV5BY2VkNmIwYTQtMDgzZi00NzNiLWEwOWYtMjg5OWMxOTc1YWJiXkEyXkFqcGdeQXVyNTk4MDczMzI@._V1_SY1000_CR0,0,569,1000_AL_.jpg"

        # determine if its going to get hotter or colder
        addMore = ''
        addMoreHeat = ''
        addMoreCold = ''
        if (tempMax - temp) > 5:
            addMoreHeat = "Its going to get pretty warm later so it might be worth wearing layers that can come off."
        if (temp - tempMin) > 5:
            addMoreCold = "Its going to get colder later so it might be worth bringing some extra layers."

        if addMoreHeat and addMoreCold:
            addMore = "Todays weather is going to fluctuate a good amount so be sure to wear layers!"
        else:
            if addMoreHeat:
                addMore = addMoreHeat
            else:
                addMore = addMoreCold

        # create and print output
        speech = "Today's weather in the %s area is %s with %s. The high for today is %s and the low is %s. We would recommend wearing %s. %s" % (cityName, temp, weatherDescription, tempMax, tempMin, whatToWear, addMore)

        handler_input.response_builder.speak(speech).set_card(
            StandardCard(SKILL_NAME, speech, Image(imageURL, imageURL)))
        return handler_input.response_builder.response


class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In HelpIntentHandler")

        handler_input.response_builder.speak(HELP_MESSAGE).ask(
            HELP_REPROMPT).set_card(SimpleCard(
                SKILL_NAME, HELP_MESSAGE))
        return handler_input.response_builder.response


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (is_intent_name("AMAZON.CancelIntent")(handler_input) or
                is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In CancelOrStopIntentHandler")

        handler_input.response_builder.speak(STOP_MESSAGE)
        return handler_input.response_builder.response


class FallbackIntentHandler(AbstractRequestHandler):
    """Handler for Fallback Intent.

    AMAZON.FallbackIntent is only available in en-US locale.
    This handler will not be triggered except in that locale,
    so it is safe to deploy on any locale.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In FallbackIntentHandler")

        handler_input.response_builder.speak(FALLBACK_MESSAGE).ask(
            FALLBACK_REPROMPT)
        return handler_input.response_builder.response


class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In SessionEndedRequestHandler")

        logger.info("Session ended reason: {}".format(
            handler_input.request_envelope.request.reason))
        return handler_input.response_builder.response


# Exception Handler
class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Catch all exception handler, log exception and
    respond with custom message.
    """
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.info("In CatchAllExceptionHandler")
        logger.error(exception, exc_info=True)

        handler_input.response_builder.speak(EXCEPTION_MESSAGE).ask(
            HELP_REPROMPT)

        return handler_input.response_builder.response


# Request and Response loggers
class RequestLogger(AbstractRequestInterceptor):
    """Log the alexa requests."""
    def process(self, handler_input):
        # type: (HandlerInput) -> None
        logger.debug("Alexa Request: {}".format(
            handler_input.request_envelope.request))


class ResponseLogger(AbstractResponseInterceptor):
    """Log the alexa responses."""
    def process(self, handler_input, response):
        # type: (HandlerInput, Response) -> None
        logger.debug("Alexa Response: {}".format(response))


# Register intent handlers
sb.add_request_handler(GetWhatToWearHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())

# Register exception handlers
sb.add_exception_handler(CatchAllExceptionHandler())

# TODO: Uncomment the following lines of code for request, response logs.
# sb.add_global_request_interceptor(RequestLogger())
# sb.add_global_response_interceptor(ResponseLogger())

# Handler name that is used on AWS lambda
lambda_handler = sb.lambda_handler()
