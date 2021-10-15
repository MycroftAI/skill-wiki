import QtQuick 2.4
import QtQuick.Controls 2.2
import QtQuick.Layouts 1.4
import org.kde.kirigami 2.4 as Kirigami
import Mycroft 1.0 as Mycroft

Mycroft.CardDelegate {
    id: root
    height: gridUnit * 26
    width: gridUnit * 46
    cardBackgroundOverlayColor: "black"

    Title {
            id: articleTitle
            anchors.top: parent.top
            fontSize: 47
            fontStyle: "Bold"
            heightUnits: 3
            text: sessionData.title
        }

    Image {
        id: featureImage
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: articleTitle.bottom
        anchors.topMargin: gridUnit * 2
        height: gridUnit * 21
        fillMode: Image.PreserveAspectFit
        source: sessionData.imgLink
    }
}
