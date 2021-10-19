import QtQuick 2.4
import QtQuick.Controls 2.2
import QtQuick.Layouts 1.4
import org.kde.kirigami 2.4 as Kirigami
import QtGraphicalEffects 1.0
import Mycroft 1.0 as Mycroft

Mycroft.CardDelegate {
    id: root
    cardBackgroundOverlayColor: "black"

    Title {
        id: articleTitle
        anchors.top: parent.top
        anchors.topMargin: Mycroft.Units.gridUnit
        anchors.horizontalCenter: parent.horizontalCenter
        fontSize: Mycroft.Units.gridUnit * 3
        fontStyle: "Bold"
        heightUnits: 3
        text: sessionData.title
    }

    Img {
        width: parent.width
        height: parent.height - Mycroft.Units.gridUnit * 6
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        imgSrc: sessionData.imgLink
    }
}
