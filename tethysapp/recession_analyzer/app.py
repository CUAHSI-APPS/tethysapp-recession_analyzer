from tethys_sdk.base import TethysAppBase, url_map_maker


class RecessionAnalyzer(TethysAppBase):
    """
    Tethys app class for Recession Analyzer.
    """

    name = 'Recession Analyzer'
    index = 'recession_analyzer:home'
    icon = 'recession_analyzer/images/icon.gif'
    package = 'recession_analyzer'
    root_url = 'recession-analyzer'
    color = '#e67e22'
    description = 'Place a brief description of your app here.'
    enable_feedback = False
    feedback_emails = []

        
    def url_maps(self):
        """
        Add controllers
        """
        UrlMap = url_map_maker(self.root_url)

        url_maps = [UrlMap(name='home',
                           url='recession-analyzer',
                           controller='recession_analyzer.controllers.home'),
                    UrlMap(name='dataframe',
                           url='dataframe',
                           controller='recession_analyzer.controllers.dataframe'),
                    UrlMap(name='flowdata',
                           url='flowdata',
                           controller='recession_analyzer.controllers.flowdata'),
         ]

        return url_maps

        
