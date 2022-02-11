// Copyright 2021, Mycroft AI Inc.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//    http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import QtQuick 2.4
import Mycroft 1.0 as Mycroft

Mycroft.CardDelegate {
    id: root
    cardBackgroundOverlayColor: "black"

    Img {
        width: Mycroft.Units.gridUnit * 3
        height: Mycroft.Units.gridUnit * 3
        anchors.top: parent.top
        anchors.topMargin: Mycroft.Units.gridUnit

        imgSrc: Qt.resolvedUrl("default-images/wikipedia-logo.svg")
    }

    Title {
        id: articleTitle
        anchors.top: parent.top
        anchors.topMargin: gridUnit
        anchors.horizontalCenter: parent.horizontalCenter
        fontSize: gridUnit * 3
        fontStyle: "Bold"
        heightUnits: 3
        text: sessionData.title
    }

    Img {
        width: parent.width
        height: parent.height - gridUnit * 6
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        imgSrc: sessionData.imgLink
    }
}
